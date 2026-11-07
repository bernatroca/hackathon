"""El cor del xat amb la IA, sense dependre de cap framework (Flask, FastAPI, Django...).

Copiat de com ho fa Armari (server/api/pregunta.php + ia.php), passat a Python:

- El navegador envia la conversa sencera; aquí s'hi posen les instruccions fixes
  (instruccions.md, al costat d'aquest fitxer). Les instruccions no venen mai del navegador.
- La clau de la IA és només al servidor (variables d'entorn o .env), mai al navegador.
- Cada missatge es reconstrueix camp a camp: no hi passa res més del que toca.
- Les captures només poden ser data URI d'imatge (les que fa el xat), poques i petites.
- La resposta surt en directe com a esdeveniments (SSE):
      data: {"tros": "..."}                      mentre escriu
      data: {"fi": true, "tallada": false, "model": "..."}   al final
      data: {"error": "..."}                     si es talla a mig camí
  Si falla ABANS de començar, és un error normal en JSON amb el seu codi (l'adaptador ho fa).
- Si la IA principal falla abans de començar a escriure, es prova la de reserva (si n'hi ha).

Només fa servir la biblioteca estàndard de Python.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterator

AQUI = Path(__file__).resolve().parent

# Límits (els mateixos d'Armari, adaptats a captures de pantalla, que necessiten més resolució).
MAX_COS = 8_000_000          # bytes de la petició sencera
MAX_MISSATGES = 60           # després, «comença una conversa nova»
MAX_IMATGES = 3              # captures per pregunta (el xat ja en limita 3)
MAX_IMATGE = 2_500_000       # caràcters de cada data URI (el xat les redueix abans)
TEMPS_MAXIM = 300            # segons: un model que raona pot trigar

DATA_URI = re.compile(r"^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$")


class ErrorXat(Exception):
    """Un error que ha d'arribar a la persona tal qual, amb el seu codi HTTP."""

    def __init__(self, estat: int, missatge: str):
        super().__init__(missatge)
        self.estat = estat
        self.missatge = missatge


# ---------- configuració ----------

def carrega_env(fitxer: Path = AQUI / ".env") -> None:
    """Llegeix un .env senzill (CLAU=valor). El que ja és a l'entorn mana."""
    if not fitxer.exists():
        return
    for linia in fitxer.read_text(encoding="utf-8").splitlines():
        linia = linia.strip()
        if not linia or linia.startswith("#") or "=" not in linia:
            continue
        clau, valor = linia.split("=", 1)
        os.environ.setdefault(clau.strip(), valor.split(" #", 1)[0].strip().strip('"').strip("'"))


def proveidors() -> list[dict]:
    """La IA principal i la de reserva, les que estiguin configurades."""
    if os.environ.get("IA_PROVA") == "1":
        return [{"nom": "prova", "url": "", "clau": "", "model": "prova"}]
    llista = []
    for prefix in ("IA", "IA_RESERVA"):
        url = os.environ.get(f"{prefix}_URL", "").strip()
        clau = os.environ.get(f"{prefix}_CLAU", "").strip()
        model = os.environ.get(f"{prefix}_MODEL", "").strip()
        if url and clau and model:
            llista.append({"nom": prefix.lower(), "url": url.rstrip("/"), "clau": clau, "model": model})
    return llista


def falta() -> str | None:
    """Què falta perquè respongui alguna IA, o None si està a punt."""
    if proveidors():
        return None
    return "Falten IA_URL, IA_CLAU i IA_MODEL al .env (o IA_PROVA=1 per provar sense IA)."


def instruccions() -> str:
    fitxer = AQUI / "instruccions.md"
    try:
        return fitxer.read_text(encoding="utf-8")
    except OSError:
        raise ErrorXat(500, "Falta instruccions.md al costat de xat_ia.py.")


def salut() -> dict:
    """El que el xat consulta en carregar: si està a punt, sense gastar res."""
    f = falta()
    p = proveidors()
    return {"ok": True, "teClau": f is None, "model": p[0]["model"] if p else None, "falta": f}


# ---------- la conversa ----------

def valida(entrada: object) -> list[dict]:
    """Torna els missatges nets, amb les instruccions al davant, o llença ErrorXat(400)."""
    missatges = entrada.get("missatges") if isinstance(entrada, dict) else None
    if not isinstance(missatges, list) or not missatges:
        raise ErrorXat(400, "Cal una llista de missatges.")
    if len(missatges) > MAX_MISSATGES:
        raise ErrorXat(413, "La conversa és massa llarga. Comença’n una de nova.")

    neta: list[dict] = [{"role": "system", "content": instruccions()}]
    for i, m in enumerate(missatges):
        esperat = "user" if i % 2 == 0 else "assistant"
        if not isinstance(m, dict) or m.get("role") != esperat:
            raise ErrorXat(400, f"El missatge {i} no té la forma que toca.")
        contingut = m.get("content")
        if esperat == "user" and isinstance(contingut, list):
            parts, imatges = [], 0
            for part in contingut:
                tipus = part.get("type") if isinstance(part, dict) else None
                if tipus == "text" and isinstance(part.get("text"), str):
                    parts.append({"type": "text", "text": part["text"]})
                    continue
                url = (part.get("image_url") or {}).get("url") if tipus == "image_url" else None
                if isinstance(url, str) and len(url) <= MAX_IMATGE and DATA_URI.match(url) and imatges < MAX_IMATGES:
                    imatges += 1
                    parts.append({"type": "image_url", "image_url": {"url": url, "detail": "high"}})
                    continue
                raise ErrorXat(400, f"Una part del missatge {i} no és ni text ni una captura que es pugui enviar.")
            neta.append({"role": "user", "content": parts})
            continue
        if not isinstance(contingut, str):
            raise ErrorXat(400, f"El missatge {i} no té la forma que toca.")
        neta.append({"role": esperat, "content": contingut})
    if len(missatges) % 2 == 0:
        raise ErrorXat(400, "L’últim missatge ha de ser una pregunta.")
    return neta


# ---------- la IA ----------
# Format «OpenAI-compatible» (/chat/completions amb stream): el parlen OpenAI, OpenRouter,
# Groq, Mistral, Ollama, LM Studio i molts altres. Si la IA que feu servir en parla un altre,
# només cal canviar _trossos_api().

class ErrorIA(Exception):
    pass


def _trossos_api(p: dict, missatges: list[dict]) -> Iterator[tuple[str, object]]:
    """Dona ("tros", text) mentre escriu i ("fi", {tallada, model}) al final."""
    cos = json.dumps({"model": p["model"], "messages": missatges, "stream": True}).encode()
    peticio = urllib.request.Request(
        f"{p['url']}/chat/completions",
        data=cos,
        headers={"Authorization": f"Bearer {p['clau']}", "Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    try:
        resposta = urllib.request.urlopen(peticio, timeout=TEMPS_MAXIM)
    except urllib.error.HTTPError as e:
        try:
            detall = json.loads(e.read().decode("utf-8", "replace")).get("error", {})
            detall = detall.get("message") if isinstance(detall, dict) else str(detall)
        except Exception:
            detall = ""
        raise ErrorIA(f"La IA ha respost {e.code}{': ' + detall if detall else ''}.")
    except (urllib.error.URLError, TimeoutError) as e:
        raise ErrorIA(f"No s’ha pogut parlar amb la IA ({getattr(e, 'reason', e)}).")

    tallada, model = False, p["model"]
    with resposta:
        for cru in resposta:
            linia = cru.decode("utf-8", "replace").strip()
            if not linia.startswith("data:"):
                continue
            dada = linia[5:].strip()
            if dada == "[DONE]":
                break
            try:
                e = json.loads(dada)
            except ValueError:
                continue
            if e.get("error"):
                raise ErrorIA(str(e["error"].get("message") if isinstance(e["error"], dict) else e["error"]))
            model = e.get("model") or model
            eleccio = (e.get("choices") or [{}])[0]
            tros = (eleccio.get("delta") or {}).get("content")
            if tros:
                yield "tros", tros
            if eleccio.get("finish_reason") == "length":
                tallada = True
    yield "fi", {"tallada": tallada, "model": model}


def _trossos_prova(missatges: list[dict]) -> Iterator[tuple[str, object]]:
    """IA_PROVA=1: una resposta inventada, per provar el xat sense clau ni cost."""
    ultima = missatges[-1]["content"]
    text = ultima if isinstance(ultima, str) else " ".join(p["text"] for p in ultima if p["type"] == "text")
    captures = 0 if isinstance(ultima, str) else sum(p["type"] == "image_url" for p in ultima)
    veu = re.search(r"<pantalla>\n(.*?)\n</pantalla>", text, re.S)
    pregunta = re.sub(r"<(context|pantalla)>\n.*?\n</\1>\n\n", "", text, flags=re.S).strip()
    resposta = (
        f"**Mode de prova** (no hi ha cap IA connectada).\n\n"
        f"- Has preguntat: «{pregunta}»\n"
        f"- Captures rebudes: {captures}\n"
        f"- Pantalla que veig: {veu.group(1) if veu else 'cap'}\n"
        f"- Missatges a la conversa: {len(missatges) - 1}\n\n"
        "Quan posis la clau de la IA al `.env`, aquí sortirà la resposta de veritat."
    )
    for paraula in re.findall(r"\S+\s*", resposta):
        time.sleep(0.03)
        yield "tros", paraula
    yield "fi", {"tallada": False, "model": "prova"}


def _trossos(p: dict, missatges: list[dict]):
    return _trossos_prova(missatges) if p["nom"] == "prova" else _trossos_api(p, missatges)


def _sse(dades: dict) -> str:
    return f"data: {json.dumps(dades, ensure_ascii=False)}\n\n"


def flux(missatges: list[dict]) -> Iterator[str]:
    """Els esdeveniments SSE de la resposta.

    El primer `next()` ja parla amb la IA: si falla abans de començar llença ErrorXat(502),
    i l'adaptador ho torna com a JSON. Després, un error va com a {"error"} dins el flux.
    """
    errors = []
    for p in proveidors():
        trossos = _trossos(p, missatges)
        try:
            primer = next(trossos)
        except (ErrorIA, StopIteration) as e:
            errors.append(str(e) or "La IA no ha tornat res.")
            continue  # la de reserva
        return _segueix(primer, trossos)
    raise ErrorXat(502, errors[-1] if errors else "Cap IA configurada.")


def _segueix(primer, trossos) -> Iterator[str]:
    escrit = False
    try:
        for tipus, valor in _amb_primer(primer, trossos):
            if tipus == "tros":
                escrit = True
                yield _sse({"tros": valor})
            else:
                if not escrit:
                    yield _sse({"error": "La IA no ha tornat cap resposta."})
                    return
                yield _sse({"fi": True, **valor})
    except ErrorIA as e:
        yield _sse({"error": str(e)})


def _amb_primer(primer, resta):
    yield primer
    yield from resta

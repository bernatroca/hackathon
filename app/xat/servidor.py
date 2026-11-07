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
import errno
import importlib
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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

def _arrel_principal() -> Path:
    arrel = AQUI.parents[1]
    try:
        comu = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=arrel, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(comu).parent
    except (OSError, subprocess.CalledProcessError):
        return arrel


def carrega_env(fitxer: Path | None = None) -> None:
    """Llegeix un .env senzill (CLAU=valor). El que ja és a l'entorn mana."""
    if fitxer is None:
        fitxer = _arrel_principal() / ".env"
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
        if prefix == "IA_RESERVA" and model:
            url = url or os.environ.get("IA_URL", "").strip()
            clau = clau or os.environ.get("IA_CLAU", "").strip()
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
                imatge = part.get("image_url") if tipus == "image_url" else None
                url = imatge.get("url") if isinstance(imatge, dict) else None
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
# Responses per defecte; IA_API=chat conserva Chat Completions.

class ErrorIA(Exception):
    pass


def _input_responses(missatges):
    """Tradueix la conversa interna al contracte de Responses, sense camps de Chat."""
    items = []
    for m in missatges:
        if m["role"] == "system":
            continue
        if m["role"] == "tool":
            items.append({"type": "function_call_output", "call_id": m["tool_call_id"],
                          "output": m["content"]})
            continue
        contingut = m.get("content")
        if isinstance(contingut, list):
            contingut = [({"type": "input_text", "text": part["text"]}
                          if part["type"] == "text" else
                          {"type": "input_image", "image_url": part["image_url"]["url"]})
                         for part in contingut]
        if contingut is not None:
            items.append({"role": m["role"], "content": contingut})
        for crida in m.get("tool_calls", []):
            items.append(crida["_responses_item"])
    return items


def _trossos_api(p: dict, missatges: list[dict]) -> Iterator[tuple[str, object]]:
    """Dona ("tros", text) mentre escriu i ("fi", {tallada, model}) al final."""
    responses = os.environ.get("IA_API", "responses").strip().lower() == "responses"
    cos = {"model": p["model"], "stream": True}
    if responses:
        cos.update(instructions="\n\n".join(m["content"] for m in missatges if m["role"] == "system"),
                   input=_input_responses(missatges), max_output_tokens=4000)
    else:
        cos["messages"] = missatges
    disponibles = _eines()
    if disponibles is not None and disponibles.EINES:
        tools = disponibles.EINES
        if responses:
            tools = [{"type": "function", **e["function"]} for e in tools]
        cos.update(tools=tools, tool_choice="auto")
    cos = json.dumps(cos).encode()
    peticio = urllib.request.Request(
        f"{p['url']}/{'responses' if responses else 'chat/completions'}",
        data=cos,
        headers={"Authorization": f"Bearer {p['clau']}", "Content-Type": "application/json", "Accept": "text/event-stream", "User-Agent": "espais-escola/1.0"},
        method="POST",
    )
    try:
        resposta = urllib.request.urlopen(peticio, timeout=TEMPS_MAXIM)
    except urllib.error.HTTPError as e:
        detall = ""
        try:
            dada = json.loads(e.read().decode("utf-8", "replace"))
            error = dada.get("error") if isinstance(dada, dict) else None
            missatge = error.get("message") if isinstance(error, dict) else None
            if isinstance(missatge, str):
                detall = _sense_claus(missatge)[:300]
        except (OSError, ValueError):
            pass
        finally:
            e.close()
        raise ErrorIA(_sense_claus(
            f"La IA ha respost HTTP {e.code}" + (f": {detall}" if detall else ".")
        )) from None
    except (OSError, urllib.error.URLError, TimeoutError) as e:
        motiu = _sense_claus(str(getattr(e, "reason", e)))
        raise ErrorIA(f"No s’ha pogut parlar amb la IA ({motiu}).") from None

    tallada, model = False, p["model"]
    crides = {}
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
            if e.get("error") or e.get("type") in ("error", "response.failed"):
                error = e.get("error") or (e.get("response") or {}).get("error") or e
                detall = error.get("message", "") if isinstance(error, dict) else str(error)
                raise ErrorIA("La IA ha retornat un error durant la resposta" +
                              (": " + _sense_claus(detall)[:300] if detall else "."))
            if responses:
                tipus = e.get("type")
                if tipus == "response.output_text.delta" and e.get("delta"):
                    yield "tros", e["delta"]
                elif tipus == "response.output_item.done":
                    item = e.get("item") or {}
                    if item.get("type") == "function_call":
                        crides[e["output_index"]] = {
                            "id": item["call_id"], "type": "function",
                            "function": {"name": item["name"], "arguments": item["arguments"]},
                            "_responses_item": item,
                        }
                elif tipus in ("response.completed", "response.incomplete"):
                    resultat = e.get("response") or {}
                    model = resultat.get("model") or model
                    tallada = (resultat.get("status") == "incomplete" and
                               (resultat.get("incomplete_details") or {}).get("reason") == "max_output_tokens")
                continue
            model = e.get("model") or model
            eleccio = (e.get("choices") or [{}])[0]
            delta = eleccio.get("delta") or {}
            for fragment in delta.get("tool_calls") or []:
                index = fragment.get("index", 0)
                crida = crides.setdefault(index, {"id": "", "type": "function",
                                                   "function": {"name": "", "arguments": ""}})
                crida["id"] += fragment.get("id") or ""
                for camp in ("name", "arguments"):
                    crida["function"][camp] += (fragment.get("function") or {}).get(camp) or ""
            tros = delta.get("content")
            if tros:
                yield "tros", tros
            if eleccio.get("finish_reason") == "length":
                tallada = True
    if crides:
        yield "tools", [crides[i] for i in sorted(crides)]
    yield "fi", {"tallada": tallada, "model": model}


def _trossos_prova(missatges: list[dict]) -> Iterator[tuple[str, object]]:
    """IA_PROVA=1: una resposta inventada, per provar el xat sense clau ni cost."""
    # Eina deliberadament falsa: el mode de prova no importa ni executa eines reals.
    resultat = _executa_prova("eco_prova", {"missatges": len(missatges) - 1})
    yield "eina", "eco_prova"
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
        f"- Missatges a la conversa: {resultat['resultat']['missatges']}\n\n"
        "Quan posis la clau de la IA al `.env`, aquí sortirà la resposta de veritat."
    )
    for paraula in re.findall(r"\S+\s*", resposta):
        time.sleep(0.03)
        yield "tros", paraula
    yield "fi", {"tallada": False, "model": "prova"}


def _eines():
    """Importació tardana: el servidor també funciona abans que arribin les eines."""
    try:
        return importlib.import_module(f"{__package__}.eines")
    except ModuleNotFoundError as exc:
        if exc.name == f"{__package__}.eines":
            return None
        raise


def _executa_prova(nom, args):
    return {"ok": True, "resultat": args, "id_sessio": [], "consulta": nom}


def _executa(crida):
    try:
        funcio = crida["function"]
        args = json.loads(funcio["arguments"])
        if not isinstance(args, dict):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        return {"ok": False, "error": "Els arguments de l'eina no són un objecte JSON vàlid."}
    disponibles = _eines()
    if disponibles is None:
        return {"ok": False, "error": "Les eines encara no estan disponibles."}
    try:
        return disponibles.executa(funcio["name"], args)
    except Exception:
        return {"ok": False, "error": "No s’ha pogut executar l’eina."}


def _trossos(p: dict, missatges: list[dict]):
    if p["nom"] == "prova":
        yield from _trossos_prova(missatges)
        return
    conversa = list(missatges)
    for _ in range(6):
        crides, contingut = [], []
        final = {"tallada": False, "model": p["model"]}
        for tipus, valor in _trossos_api(p, conversa):
            if tipus == "tools":
                crides.extend(valor)
            elif tipus == "tros":
                contingut.append(valor)
                yield tipus, valor
            elif tipus == "fi":
                final = valor
        if not crides:
            yield "fi", final
            return
        conversa.append({"role": "assistant", "content": "".join(contingut) or None,
                         "tool_calls": crides})
        for crida in crides:
            yield "eina", crida["function"]["name"]
            resultat = _executa(crida)
            conversa.append({"role": "tool", "tool_call_id": crida["id"],
                             "content": "<dades>\n" + json.dumps(resultat, ensure_ascii=False)
                             + "\n</dades>"})
    yield "tros", "No he pogut acabar la consulta en sis voltes. Pots concretar la pregunta?"
    yield "fi", {"tallada": False, "model": p["model"]}


def _sense_claus(text):
    for prefix in ("IA", "IA_RESERVA"):
        clau = os.environ.get(f"{prefix}_CLAU")
        if clau:
            text = text.replace(clau, "[clau oculta]")
    return text


def _neteja_secrets(valor):
    if isinstance(valor, str):
        return _sense_claus(valor)
    if isinstance(valor, dict):
        return {k: _neteja_secrets(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_neteja_secrets(v) for v in valor]
    return valor


def _sse(dades: dict) -> str:
    return f"data: {json.dumps(_neteja_secrets(dades), ensure_ascii=False)}\n\n"


def flux(missatges: list[dict]) -> Iterator[str]:
    """Els esdeveniments SSE de la resposta.

    El primer `next()` ja parla amb la IA: si falla abans de començar llença ErrorXat(502),
    i l'adaptador ho torna com a JSON. Després, un error va com a {"error"} dins el flux.
    """
    trossos = _amb_reserva(missatges)
    try:
        primer = next(trossos)
    except (ErrorIA, StopIteration) as exc:
        raise ErrorXat(502, str(exc) or "Cap IA configurada.") from None
    return _segueix(primer, trossos)


def _amb_reserva(missatges):
    error = "Cap IA configurada."
    for p in proveidors():
        escrit = False
        try:
            for tipus, valor in _trossos(p, missatges):
                if tipus == "tros" and valor:
                    escrit = True
                yield tipus, valor
            return
        except ErrorIA as exc:
            error = _sense_claus(str(exc)) or "No s’ha pogut obtenir una resposta de la IA."
            if escrit:
                raise ErrorIA(error) from None
    raise ErrorIA(error)


def _segueix(primer, trossos) -> Iterator[str]:
    escrit = False
    try:
        for tipus, valor in _amb_primer(primer, trossos):
            if tipus == "tros":
                escrit = True
                yield _sse({"tros": valor})
            elif tipus == "eina":
                yield _sse({"eina": valor})
            elif tipus == "fi":
                if not escrit:
                    yield _sse({"error": "La IA no ha tornat cap resposta."})
                    return
                yield _sse({"fi": True, **valor})
    except ErrorIA as e:
        yield _sse({"error": str(e)})


def _amb_primer(primer, resta):
    yield primer
    yield from resta


ORIGENS = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d{1,5})?$")


class Handler(BaseHTTPRequestHandler):
    """Adaptador HTTP; no registra ni el cos ni errors dels proveïdors."""

    def log_message(self, format, *args):
        pass

    def _capcaleres(self, estat, tipus):
        self.send_response(estat)
        self.send_header("Content-Type", tipus)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Vary", "Origin")
        origen = self.headers.get("Origin")
        if origen is not None and ORIGENS.fullmatch(origen):
            self.send_header("Access-Control-Allow-Origin", origen)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

    def _json(self, estat, dada):
        self._capcaleres(estat, "application/json; charset=utf-8")
        self.wfile.write(json.dumps(_neteja_secrets(dada), ensure_ascii=False).encode())

    def _accepta(self):
        if self.path != "/api/xat":
            self._json(404, {"error": "Ruta desconeguda."})
            return False
        origen = self.headers.get("Origin")
        if origen is not None and not ORIGENS.fullmatch(origen):
            self._json(403, {"error": "Origen no permès."})
            return False
        return True

    def do_OPTIONS(self):
        if self._accepta():
            self._capcaleres(204, "text/plain")

    def do_GET(self):
        if self._accepta():
            self._json(200, salut())

    def do_POST(self):
        if not self._accepta():
            return
        try:
            try:
                longitud = int(self.headers.get("Content-Length", ""))
            except ValueError:
                raise ErrorXat(400, "Falta una longitud vàlida de la petició.")
            if longitud < 0:
                raise ErrorXat(400, "La longitud no és vàlida.")
            if longitud > MAX_COS:
                raise ErrorXat(413, "La conversa és massa llarga. Comença’n una de nova.")
            if self.headers.get("Transfer-Encoding"):
                raise ErrorXat(400, "El format de la petició no és vàlid.")
            if falta():
                raise ErrorXat(503, "La IA encara no està a punt.")
            try:
                entrada = json.loads(self.rfile.read(longitud))
            except (ValueError, UnicodeError):
                raise ErrorXat(400, "La petició no és JSON.")
            esdeveniments = flux(valida(entrada))
        except ErrorXat as exc:
            self._json(exc.estat, {"error": exc.missatge})
            return
        self._capcaleres(200, "text/event-stream; charset=utf-8")
        try:
            for esdeveniment in esdeveniments:
                self.wfile.write(esdeveniment.encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


_servidor = None
_url_reutilitzada = None
_fil = None
_pany = threading.Lock()


def arrenca(port: int = 8502) -> str:
    """Arrenca una sola instància local per procés, també amb crides concurrents."""
    global _servidor, _fil, _url_reutilitzada
    with _pany:
        if _url_reutilitzada is not None:
            return _url_reutilitzada
        if _servidor is None:
            carrega_env()
            try:
                servidor = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            except OSError as exc:
                if exc.errno != errno.EADDRINUSE:
                    raise
                url = f"http://127.0.0.1:{port}/api/xat"
                try:
                    with urllib.request.urlopen(url, timeout=2) as resposta:
                        dada = json.load(resposta)
                    if not isinstance(dada, dict) or dada.get("ok") is not True:
                        raise ValueError("No és el servidor del xat")
                except (OSError, ValueError):
                    raise RuntimeError(
                        f"El port {port} està ocupat i no respon com un servidor del xat. "
                        "Allibera el port o tria’n un altre."
                    ) from None
                _url_reutilitzada = url
                return url
            fil = threading.Thread(target=servidor.serve_forever, daemon=True)
            fil.start()
            _servidor, _fil = servidor, fil
        return f"http://127.0.0.1:{_servidor.server_address[1]}/api/xat"

"""Preguntes comprovables: python -m app.xat.pregunta \"Quantes aules…?\".

No arrenca cap servidor HTTP. Comparteix el flux i la comprovació amb el navegador.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import servidor


def _mostra_consultes(consultes):
    print("\nConsultes:")
    if not consultes:
        print("(cap)")
    for c in consultes:
        print(c["eina"] + " " + json.dumps(c.get("args", {}), ensure_ascii=False))
        codis = list(dict.fromkeys([
            *c.get("id_sessio", []),
            *servidor._CODIS.findall(json.dumps(c.get("resultat"), ensure_ascii=False)),
        ]))
        print("  id_sessio / aules: " + (", ".join(codis) or "(cap al resultat)"))
        if not c.get("ok"):
            print("  Error: " + c.get("error", "Consulta fallida"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pregunta", nargs="?")
    parser.add_argument("--proposta", choices=("avui", "5.1", "5.2", "5.3", "5.4"))
    parser.add_argument("--setmana")
    parser.add_argument("--sense-ia", action="store_true")
    parser.add_argument("--eina")
    parser.add_argument("--args", default="{}", help="Arguments de l'eina en JSON")
    op = parser.parse_args(argv)
    if op.sense_ia:
        if not op.eina:
            parser.error("--sense-ia necessita --eina")
        try:
            args = json.loads(op.args)
        except ValueError:
            parser.error("--args ha de ser un objecte JSON vàlid")
        if not isinstance(args, dict):
            parser.error("--args ha de ser un objecte JSON vàlid")
        crida = {"function": {"name": op.eina, "arguments": json.dumps(args)}}
        resultat = servidor._executa(crida)
        consulta = servidor._resum_consulta(op.eina, args, resultat)
        print("Resultat: " + json.dumps(consulta.get("resultat", {}), ensure_ascii=False))
        _mostra_consultes([consulta])
        return 0 if resultat.get("ok") else 1
    if not op.pregunta:
        parser.error("Cal una pregunta o --sense-ia --eina NOM --args JSON")
    if op.eina or op.args != "{}":
        parser.error("--eina i --args necessiten --sense-ia")
    pantalla = []
    if op.proposta:
        pantalla.append("Proposta: " + op.proposta)
    if op.setmana:
        pantalla.append("Setmana: " + op.setmana)
    text = op.pregunta
    if pantalla:
        text = "<pantalla>\n" + ". ".join(pantalla) + "\n</pantalla>\n\n" + text
    # Mateixa configuració que l'app, sense servidor HTTP ni navegador.
    servidor.carrega_env()
    if servidor.falta():
        print(servidor.falta(), file=sys.stderr)
        return 1
    consultes, resposta, error = [], [], None
    try:
        for bloc in servidor.flux(servidor.valida({"missatges": [{"role": "user", "content": text}]})):
            event = json.loads(bloc[6:])
            if "tros" in event:
                resposta.append(event["tros"])
            if "consultes" in event:
                consultes = event["consultes"]
            if "error" in event:
                error = event["error"]
    except servidor.ErrorXat as exc:
        error = str(exc)
    if resposta:
        print("".join(resposta))
    _mostra_consultes(consultes)
    if error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

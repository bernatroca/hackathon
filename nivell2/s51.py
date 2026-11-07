"""Executa el 5.1, mantenint totes les franges de partida."""
import argparse
import json
import time
from nivell2.base import carrega_model, carrega_oficial, Proposta, RESULTATS, verifica, avalua_rapid, PYTHON, REPTE
from nivell2.aules import assigna_aules


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--temps', type=float, default=300)
    parser.add_argument('--llavor', type=int, default=0)
    args = parser.parse_args()
    start = time.monotonic()
    base = carrega_model()
    rooms, status = assigna_aules(base, {sid: (s.data, s.ini) for sid, s in base.sessions.items()}, temps_s=args.temps, llavor=args.llavor)
    if not rooms:
        raise RuntimeError(f'Sense assignació: {status}')
    prop = Proposta.de_base(base)
    for sid, a in rooms.items():
        prop.files[sid].aula = a
    out = RESULTATS / '5.1'
    path = prop.escriu(out / 'proposta.csv')
    report = verifica(path, nomes_aules=True, json_path=out/'informe.json', violacions_path=out/'violacions.csv')
    official = carrega_oficial()
    before = avalua_rapid(official, Proposta.de_base(official), nomes_aules=True).objectius
    elapsed = time.monotonic()-start
    summary = {'estat_solver': status, 'temps_total_s': round(elapsed, 3), 'abans': before, 'despres': report.objectius}
    (out/'comparacio.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    (out/'README.md').write_text(f'''# 5.1 Aules

Generar des del worktree:
```sh
{PYTHON} -m nivell2.s51 --temps {args.temps:g} --llavor {args.llavor}
```
Verificar:
```sh
cd {REPTE}
{PYTHON} -m horaris check {path} --semestre 2 --nomes-aules --json {out}/informe.json --violacions {out}/violacions.csv
```

Estat: {status}. Veredicte oficial: {report.veredicte}. Temps total: {elapsed:.3f} s.
Objectius abans/després: `comparacio.json`. Cap relaxació.

SUPÒSITS: pes 1 per aula base de teoria; franges incompletes són un error.
Rutina prioritària; només s'admeten excepcions si el model estricte és INFEASIBLE.
Els defectes d'aforament de sessions fixades amb aula inalterada es mantenen com
a heretats, tal com exigeix R1 i els tracta el verificador oficial.

Proves: `{PYTHON} -m pytest nivell2/test_aules.py`. En l'entorn de treball
aquest Python no disposa de pytest; les 8 funcions de prova s'han executat
directament amb runpy (totes correctes, menys d'1 segon).
''')
    print(report.veredicte, status, f'{elapsed:.3f} s')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not report.valida:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

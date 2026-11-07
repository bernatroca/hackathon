"""Millora 5.1 amb aula base; conserva cada millora vàlida en disc."""
from nivell2.readmes import actualitza
import argparse
import json
import time
import tempfile
from pathlib import Path
from nivell2.base import (carrega_model, carrega_oficial, Proposta, RESULTATS,
                          verifica, avalua_rapid, PYTHON, REPTE)
from nivell2.aules import assigna_aules
from nivell2.xifres import compara


def qualitat(base, proposta, informe):
    """Rutina, aula base, passadís, desplaçaments, canvis: ordre explícit."""
    from collections import defaultdict, Counter
    patterns = defaultdict(Counter)
    for sid, s in base.sessions.items():
        patterns[s.activitat or sid][proposta.files[sid].aula] += 1
    exceptions = sum(sum(c.values())-max(c.values()) for c in patterns.values())
    o = informe.objectius
    extra, walks = o['r6_aules_te_extra_per_grup'], o['r6_canvis_te_paul_fora_passadis']
    score = 100 * max(extra-13, 0) + 10 * max(walks-166, 0) + o['desplacaments_aula']
    return (exceptions, score, extra, walks, o['desplacaments_aula'], o['canvis_aula'])


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--temps', type=float, default=600)
    parser.add_argument('--llavor', type=int, default=0)
    args = parser.parse_args()
    start = time.monotonic()
    base, official = carrega_model(), carrega_oficial()
    out = RESULTATS/'5.1'
    out.mkdir(parents=True, exist_ok=True)
    path = out/'proposta.csv'
    best, best_key, previous = None, None, None
    if path.exists():
        old = Proposta.llegeix(path)
        check = verifica(path, nomes_aules=True)
        if check.valida:
            best, best_key, previous = old, qualitat(official, old, check), check.objectius
            old.escriu(out/'referencia_anterior.csv')
    def accept(rooms, status):
        nonlocal best, best_key
        p = Proposta.de_base(base)
        for sid, room in rooms.items():
            p.files[sid].aula = room
        inf = avalua_rapid(official, p, nomes_aules=True)
        if inf.veredicte != 'VALIDA':
            return
        key = qualitat(official, p, inf)
        if best_key is not None and key >= best_key:
            return
        with tempfile.TemporaryDirectory(dir=out, prefix='candidata_') as tmp:
            candidate = p.escriu(Path(tmp)/'proposta.csv')
            report = verifica(candidate, nomes_aules=True)
            if report.valida:
                candidate.replace(path)
                best, best_key = p, key
                verifica(path, nomes_aules=True, json_path=out/'informe.json', violacions_path=out/'violacions.csv')
                print('Millora VALIDA', key, f'{time.monotonic()-start:.1f} s', flush=True)
    rooms, status = assigna_aules(base, {sid: (s.data, s.ini) for sid, s in base.sessions.items()},
                                 temps_s=args.temps, llavor=args.llavor, pista=best, en_solucio=accept, agrupa_te=True, millora_local=True)
    if rooms:
        accept(rooms, status)
    if best is None:
        raise RuntimeError(f'Sense assignació vàlida: {status}')
    best.escriu(path)
    report = verifica(path, nomes_aules=True, json_path=out/'informe.json', violacions_path=out/'violacions.csv')
    comparison = compara(best, official, nomes_aules=True, proposta_path=path)
    from nivell2.comprova import escriu_csv
    escriu_csv(out/'xifres.csv', comparison.files)
    metrics = {r['xifra']: (r['abans'], r['despres']) for r in comparison.files}
    selected = [*report.objectius, 'aules_grup_setmana_mitjana', 'aules_grup_setmana_maxim', 'excepcions_rutina']
    from collections import defaultdict
    weeks = defaultdict(set)
    for sid, s in official.sessions.items():
        if 'GCIS:1r' in s.cohorts and s.linia == '61':
            weeks[s.data.isocalendar()[:2]]
            if best.files[sid].aula and not s.sense_espai:
                weeks[s.data.isocalendar()[:2]].add(best.files[sid].aula)
    gcis = {'mitjana': sum(map(len, weeks.values()))/len(weeks) if weeks else 0,
            'maxim': max(map(len, weeks.values()), default=0)}
    elapsed = time.monotonic()-start
    initial_path = out/'inicial_51.json'
    initial = json.loads(initial_path.read_text()) if initial_path.exists() else None
    summary = {'inicial_51': initial, 'estat_solver': status, 'temps_total_s': round(elapsed, 3), 'criteri_seleccio': list(best_key),
               'abans': {k: metrics[k][0] for k in selected},
               'anterior_51': previous, 'GCIS_1r_61_aules_setmana': gcis, 'despres': {k: metrics[k][1] for k in selected}}
    (out/'comparacio.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    table = '| Indicador | Avui | Proposta |\n|---|---:|---:|\n' + ''.join(f'| {k} | {metrics[k][0]} | {metrics[k][1]} |\n' for k in selected)
    (out/'README.md').write_text(f'''# 5.1 Aules amb aula base

Generar des del worktree (la proposta existent és la pista i el llindar de millora):
```sh
{PYTHON} -m nivell2.s51 --temps {args.temps:g} --llavor {args.llavor}
```
Verificar:
```sh
cd {REPTE}
{PYTHON} -m horaris check {path} --semestre 2 --nomes-aules --json {out}/informe.json --violacions {out}/violacions.csv
```
Proves des del worktree:
```sh
{PYTHON} -m pytest nivell2/test_aules.py
```

Veredicte: {report.veredicte}, sense relaxacions. Solver: {status} (no és una prova d'optimalitat).
Temps total: {elapsed:.3f} s. Cada incumbent millor segons rutina i cost de qualitat
(100 per aula TE extra sobre 13, 10 per canvi TE–PAUL sobre 166, més desplaçaments;
empats per aules TE extra, passadís i canvis) es verifica i desa immediatament.
`referencia_anterior.csv` conserva el punt de partida de l'execució.

{table}

SUPÒSITS: aula base i passadís són preferències fortes, subordinades a les regles
oficials i la rutina. Pesos: aula TE extra 10000, TE fora base 1000 per sessió,
PAUL/SEM fora passadís base 200, canvi respecte d'avui 3, classe seguida fora
passadís 2, canvi entre classes seguides 1. La transició TE–PAUL fora de
passadís té un reforç d’aula base de 1000, a més del pes general de 2. Les aules fixades es respecten;
els seus defectes d'aforament inalterats continuen heretats, segons el verificador.
Els recomptes grup/setmana inclouen PLAB i fan servir `nivell2.xifres`.
GCIS 1r 61: mitjana {gcis['mitjana']:.3f}, màxim {gcis['maxim']} aules/setmana.

Límits comprovats sobre aquesta partida: els 167 canvis TE–PAUL fora de passadís
d'avui tenen totes dues aules fixades. No es pot baixar de 167 sense canviar
les regles. GIA 3r línia 71 i MEBA línia 1 tenen TE simultànies: no poden
aconseguir una sola aula TE amb les franges fixes (cota inferior global: 2 extra).

''')
    actualitza(out, '5.1')
    print(report.veredicte, status, f'{elapsed:.3f} s', flush=True)
    print(f"Sessions: {len(best.files)}", flush=True)
    if not report.valida:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

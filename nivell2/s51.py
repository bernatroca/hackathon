"""Millora 5.1 amb aula base; conserva cada millora vàlida en disc."""
from nivell2.readmes import actualitza, conserva_seccions, arrodoneix_text
import argparse
import csv
from collections import defaultdict
import json
import time
import tempfile
from pathlib import Path
from nivell2.base import (carrega_model, carrega_oficial, Proposta, Assignacio, RESULTATS,
                          verifica, avalua_rapid, PYTHON, REPTE)
from nivell2.aules import assigna_aules, qualitat_aules
from nivell2.xifres import compara


def qualitat(base, proposta, informe=None):
    """El mateix criteri que minimitza assigna_aules, també per recuperar CSV."""
    return qualitat_aules(base, {sid: a.aula for sid, a in proposta.files.items()})


def llegeix_proposta(path):
    """Admet espais perifèrics i majúscules; rebutja duplicats abans del dict."""
    files = {}
    with open(path, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            r = {k.strip().lower(): (v or '').strip() for k, v in row.items() if k is not None}
            sid = r['id_sessio'].upper()
            if sid in files:
                raise ValueError('La proposta té identificadors duplicats')
            files[sid] = Assignacio(r['dia'].upper(), r['h_ini'], r['aula'].upper(), r.get('data', ''))
    return Proposta(files)


def aforament_model_ok(base, proposta):
    """Suma la classe física amb alumnes estimats; exempció fixada inalterada."""
    if proposta.files.keys() != base.sessions.keys():
        return False
    units = defaultdict(list)
    for sid, s in base.sessions.items():
        if not s.sense_espai:
            units[s.unitat].append(s)
    for ss in units.values():
        rooms = {proposta.files[s.id].aula for s in ss}
        if len(rooms) != 1:
            return False
        room = next(iter(rooms))
        if room in base.aules and sum(s.alumnes for s in ss) > base.aules[room].capacitat:
            if not all(s.fixada and s.aula == room for s in ss):
                return False
    return True


def extres_sense_dobles(base, proposta):
    # Preserve the official definition (including missing rooms), removing
    # only the rows that do not represent physical room demand.
    from copy import copy
    physical = copy(base)
    physical.sessions = {sid: s for sid, s in base.sessions.items() if not s.sense_espai}
    p = Proposta({sid: proposta.files[sid] for sid in physical.sessions})
    return avalua_rapid(physical, p, nomes_aules=True).objectius['r6_aules_te_extra_per_grup']


def comparacio_extres(base, proposta):
    return {'r6_aules_te_extra_sense_dobles': (
        extres_sense_dobles(base, Proposta.de_base(base)), extres_sense_dobles(base, proposta))}


def restauracions_referencia(base):
    """Blocs d'activitats compartides que poden recuperar una aula original."""
    activities, units = defaultdict(set), defaultdict(set)
    for sid, s in base.sessions.items():
        if not s.sense_espai:
            activities[s.activitat or sid].add(sid)
            units[s.unitat].add(sid)
    pending = set(base.sessions)
    for ids in activities.values():
        if not ids & pending:
            continue
        block = set(ids)
        todo = list(ids)
        while todo:
            s = base.sessions[todo.pop()]
            linked = activities[s.activitat or s.id] | units[s.unitat]
            todo.extend(linked - block)
            block.update(linked)
        pending.difference_update(block)
        rooms = {base.sessions[sid].aula for sid in block}
        if len(rooms) == 1 and next(iter(rooms)):
            yield block, next(iter(rooms))


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
        old = llegeix_proposta(path)
        with tempfile.TemporaryDirectory(dir=out, prefix='recuperada_') as tmp:
            check = verifica(old.escriu(Path(tmp)/'proposta.csv'), nomes_aules=True)
        previous = check.objectius
        print('Anterior 5.1:', json.dumps(previous, ensure_ascii=False), flush=True)
        if check.valida and aforament_model_ok(base, old):
            best, best_key = old, qualitat(base, old)
            old.escriu(out/'referencia_anterior.csv')
        else:
            print('Proposta anterior descartada: verificació o aforament del model.', flush=True)
    def accept(rooms, status):
        nonlocal best, best_key
        p = Proposta.de_base(base)
        for sid, room in rooms.items():
            p.files[sid].aula = room
        if not aforament_model_ok(base, p):
            return
        inf = avalua_rapid(official, p, nomes_aules=True)
        if inf.veredicte != 'VALIDA':
            return
        key = qualitat(base, p)
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
    if best is not None:
        for ids, room in restauracions_referencia(base):
            if time.monotonic() - start >= args.temps:
                break
            if all(best.files[sid].aula == room for sid in ids):
                continue
            rooms = {sid: a.aula for sid, a in best.files.items()}
            rooms.update(dict.fromkeys(ids, room))
            if qualitat_aules(base, rooms) < best_key:
                accept(rooms, 'RESTAURACIO')
    rooms, status = assigna_aules(base, {sid: (s.data, s.ini) for sid, s in base.sessions.items()},
                                 temps_s=max(.01, args.temps - (time.monotonic()-start)), llavor=args.llavor, pista=best, en_solucio=accept, agrupa_te=True, millora_local=True)
    if rooms:
        accept(rooms, status)
    if best is None:
        raise RuntimeError(f'Sense assignació vàlida: {status}')
    best.escriu(path)
    report = verifica(path, nomes_aules=True, json_path=out/'informe.json', violacions_path=out/'violacions.csv')
    comparison = compara(best, official, nomes_aules=True, proposta_path=path)
    from nivell2.comprova import escriu_csv
    metrics = {r['xifra']: (r['abans'], r['despres']) for r in comparison.files}
    extra_metrics = comparacio_extres(official, best)
    metrics.update(extra_metrics)
    comparison.files.extend({'xifra': k, 'abans': a, 'despres': d} for k, (a, d) in extra_metrics.items())
    escriu_csv(out/'xifres.csv', comparison.files)
    selected = [*report.objectius, 'aules_grup_setmana_mitjana', 'aules_grup_setmana_maxim', 'excepcions_rutina', 'r6_aules_te_extra_sense_dobles']
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
               'criteri': 'rutina, aules TE extra sense dobles, 3·canvis aula + 2·canvis fora passadís',
               'nota_dobles': 'El recompte oficial inclou dobles sense espai propi; el recompte sense dobles reflecteix la demanda física d’aules.',
               'abans': {k: metrics[k][0] for k in selected},
               'anterior_51': previous, 'GCIS_1r_61_aules_setmana': gcis, 'despres': {k: metrics[k][1] for k in selected}}
    (out/'comparacio.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    table = '| Indicador | Avui | Proposta |\n|---|---:|---:|\n' + ''.join(f'| {k} | {metrics[k][0]} | {metrics[k][1]} |\n' for k in selected)
    anterior_readme = out/'README.md'
    anterior_text = anterior_readme.read_text(encoding='utf-8') if anterior_readme.exists() else ''
    (out/'README.md').write_text(arrodoneix_text(conserva_seccions(f'''# 5.1 Aules amb aula base

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
Temps total: {elapsed:.3f} s. Cada incumbent millor segons el criteri únic
(rutina, aula base TE sense dobles, cost 3 per canvi respecte d’avui + 2 per
canvi entre classes seguides fora del passadís) es verifica i desa immediatament.
Les prioritats són lexicogràfiques, sense llindars arbitraris.
`referencia_anterior.csv` conserva el punt de partida de l'execució.

{table}

El recompte oficial inclou dobles sense espai propi; el recompte sense dobles
reflecteix la demanda física d’aules (avui {metrics['r6_aules_te_extra_sense_dobles'][0]} → {metrics['r6_aules_te_extra_sense_dobles'][1]}, al costat de l’oficial).

SUPÒSITS: rutina i aula base TE tenen prioritat; entre solucions equivalents,
els pesos de l’especificació són canvi respecte d’avui 3 i canvi entre classes
seguides fora de passadís 2. Solver i selector apliquen el mateix criteri.
Les unions TE són una pista: també es prova sense unions si queda temps.
Es comprova l’aforament amb les xifres del model, incloses les estimacions;
els defectes fixats inalterats es mantenen només si són heretats.
Els recomptes grup/setmana inclouen PLAB i fan servir `nivell2.xifres`.
GCIS 1r 61: mitjana {gcis['mitjana']:.3f}, màxim {gcis['maxim']} aules/setmana.

''', anterior_text)))
    actualitza(out, '5.1')
    print('Comparació 5.1:', json.dumps({k: metrics[k] for k in selected}, ensure_ascii=False), flush=True)
    print(report.veredicte, status, f'{elapsed:.3f} s', flush=True)
    print(f"Sessions: {len(best.files)}", flush=True)
    if not report.valida:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

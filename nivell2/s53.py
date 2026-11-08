"""5.3: quatre contingències simultànies sobre el 5.2 congelat."""
from __future__ import annotations
from nivell2.readmes import normalitza

import argparse
import json
import shlex
import re
import tempfile
from pathlib import Path
import time
from collections import Counter

from nivell2.base import (CONTINGENCIES, RESULTATS, RESULTATS_PRINCIPAL,
                          PYTHON, REPTE, Proposta, carrega_model, verifica, fmt)
from nivell2.reparacio import Canvi, afectades, comprova_reserva_operativa, repara
from nivell2.franges import _referencia
from nivell2.imprevistos import TEMPS_REPARACIO
from nivell2.s52 import escriu_csv
from horaris.model import llegeix_relaxacions


def resum_relaxacions(rows):
    """Només recomptes; no copia identificadors al resum."""
    counts = Counter()
    for r in rows:
        counts[r['restriccio'], r['justificacio']] += len(set(filter(None, r['sessions'].split('|'))))
    return [{'restriccio': rule, 'motiu': why, 'sessions': n}
            for (rule, why), n in sorted(counts.items())]


def recomptes_proposta(base, proposta, referencia, canvi):
    """Comparació amb el 5.2: només recomptes, sense files ni identificadors."""
    afectades_directes = set().union(*afectades(referencia, canvi).values())
    franges = {sid for sid, s in base.sessions.items()
               if _referencia(s, proposta) != _referencia(s, referencia)}
    aules = {sid for sid in base.sessions
             if proposta.files[sid].aula != referencia.files[sid].aula}
    minim, _ = comprova_reserva_operativa(base, proposta)
    return {'canvis_aula_vs_referencia': len(aules-set(base.cancellades)),
            'canvis_franja_vs_referencia': len(franges),
            'classes_suport': len((franges | aules)-afectades_directes),
            'reserva_minima_operativa': minim}


def _mostra_deficits(deficits):
    for d in deficits:
        print('ERROR reserva operativa:', d['data'].isoformat(),
              fmt(d['franja'])+'–'+fmt(d['franja']+60),
              '; aules lliures:', ', '.join(d['lliures']) or 'cap',
              '; aules tancades:', ', '.join(d['tancades']) or 'cap',
              '; aules ocupades:', ', '.join(d['ocupades']) or 'cap')


def regressio_oficial(anterior, nova):
    """Una reserva igual o pitjor no justifica més canvis oficials."""
    keys = ('canvis_franja_vs_referencia', 'canvis_aula_vs_referencia')
    return (anterior['reserva_minima_operativa'] >= nova['reserva_minima_operativa']
            and sum(nova[k] for k in keys) > sum(anterior[k] for k in keys))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--temps', type=float, default=TEMPS_REPARACIO)
    ap.add_argument('--llavor', type=int, default=0)
    ap.add_argument('--comprova-determinisme', action='store_true',
                    help='genera dues vegades i exigeix CSV idèntics abans de publicar')
    args = ap.parse_args(argv)
    if not 0 < args.temps <= TEMPS_REPARACIO:
        ap.error(f'El pressupost ha de ser superior a zero i com a màxim de {TEMPS_REPARACIO} segons')
    start = time.monotonic()
    RESULTATS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.5.3-', dir=RESULTATS) as temporary:
        stage = Path(temporary)/'5.3'
        status = _genera(args, stage, start)
        if status:
            return status
        if args.comprova_determinisme:
            repeat = Path(temporary)/'repeticio'
            status = _genera(args, repeat, time.monotonic())
            if status:
                return status
            if (stage/'proposta.csv').read_bytes() != (repeat/'proposta.csv').read_bytes():
                print('Determinisme: ERROR; les dues execucions produeixen CSV diferents')
                return 1
            print('Determinisme: CORRECTE; CSV idèntic en dues execucions seguides')
        # Es publica tota la carpeta validada. Si falla el segon rename,
        # es restaura íntegrament el lliurament anterior.
        destination = RESULTATS/'5.3'
        backup = Path(temporary)/'anterior'
        if destination.exists():
            destination.rename(backup)
        try:
            stage.rename(destination)
        except Exception:
            if backup.exists():
                backup.rename(destination)
            raise
    return 0


def _genera(args, out, start):
    out.mkdir(parents=True, exist_ok=True)
    refpath = RESULTATS/'5.2'/'proposta.csv'
    if not refpath.is_file():
        refpath = RESULTATS_PRINCIPAL/'5.2'/'proposta.csv'
    relaxpath = refpath.parent/'relaxacions.csv'
    # Llegeixen les dades només el model i la reparació; cap fila va a stdout.
    reference = Proposta.llegeix(refpath)
    inherited = [{'restriccio': r.restriccio, 'sessions': '|'.join(sorted(r.sessions)),
                  'justificacio': re.sub(r'(?<![\w/])diagnostic\.md', '../5.2/diagnostic.md', r.justificacio)} for r in llegeix_relaxacions(relaxpath)]
    before_report = verifica(refpath, relaxacions=relaxpath)
    if before_report.veredicte not in ('VALIDA', 'VALIDA AMB RELAXACIONS DECLARADES'):
        raise ValueError('Cal una referència 5.2 validada abans de reparar-la')
    base = carrega_model(CONTINGENCIES)
    canvi = Canvi(base, carrega_model(), args.temps, args.llavor)
    result = repara(reference, canvi)
    (out/'execucio.json').write_text(json.dumps(result.estadistiques, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if result.proposta is None:
        print('Reparació sense proposta:', result.estat, '; intents:', len(result.estadistiques['intents']))
        _mostra_deficits(comprova_reserva_operativa(base, reference)[1])
        for attempt in result.estadistiques['intents']:
            print('Nivell:', attempt['nivell'], '; sessions obertes:', attempt['sessions_obertes'])
            for label, n in attempt.get('diagnostic', {}).items():
                print(label+':', n)
        return 1
    if result.estat != 'OPTIMAL':
        print('ERROR: estat solver:', result.estat, '; cal OPTIMAL; no es publica el 5.3')
        return 1
    minimum, deficits = comprova_reserva_operativa(base, result.proposta)
    if minimum < 2:
        print('ERROR: reserva mínima operativa:', minimum, '; no es publica el 5.3')
        _mostra_deficits(deficits)
        return 1
    path = result.proposta.escriu(out/'proposta.csv')
    rows = inherited+result.relaxacions
    relax = out/'relaxacions.csv'
    escriu_csv(relax, rows, ['restriccio', 'sessions', 'justificacio'])
    report = verifica(path, escenari=CONTINGENCIES, referencia=refpath,
                      relaxacions=relax, json_path=out/'informe.json',
                      violacions_path=out/'violacions.csv')
    if report.veredicte not in ('VALIDA', 'VALIDA AMB RELAXACIONS DECLARADES') or report.compten():
        print('ERROR: verificació oficial:', report.veredicte, '; no es publica el 5.3')
        return 1
    elapsed = time.monotonic()-start
    summary = {k: result.estadistiques[k] for k in
               ('sessions_afectades', 'sessions_afectades_per_imprevist', 'sessions_obertes')}
    summary.update({k: report.objectius[k] for k in
                    ('canvis_franja_vs_referencia', 'canvis_aula_vs_referencia')})
    summary.update(canvis_franja_model=result.estadistiques['canvis_franja_vs_referencia'],
                   canvis_aula_model=result.estadistiques['canvis_aula_vs_referencia'],
                   relaxacions_per_motiu=resum_relaxacions(rows),
                   relaxacions_noves=sum(len(r['sessions'].split('|')) for r in result.relaxacions),
                   incompliments_no_declarats=sum(report.compten().values()),
                   veredicte=report.veredicte, temps_s=round(elapsed, 3),
                   estat_solver=result.estat,
                   optim_global_demostrat=False)
    counts = recomptes_proposta(base, result.proposta, reference, canvi)
    counts.update({k: report.objectius[k] for k in
                   ('canvis_franja_vs_referencia', 'canvis_aula_vs_referencia')})
    summary.update(reserva_minima_operativa=minimum, classes_suport=counts['classes_suport'])
    previous = RESULTATS/'5.3'/'proposta.csv'
    if previous.is_file():
        summary['comparacio_anterior'] = {
            'abans': recomptes_proposta(base, Proposta.llegeix(previous), reference, canvi),
            'despres': counts}
        old = summary['comparacio_anterior']['abans']
        if regressio_oficial(old, counts):
            print('ERROR: regressió respecte del 5.3 publicat; no es publica la proposta nova')
            print('Canvis oficials (franja + aula):',
                  old['canvis_franja_vs_referencia']+old['canvis_aula_vs_referencia'], '→',
                  counts['canvis_franja_vs_referencia']+counts['canvis_aula_vs_referencia'])
            print('Reserva mínima operativa:', old['reserva_minima_operativa'], '→', minimum)
            return 1
    public_summary = {k: v for k, v in summary.items() if k != 'comparacio_anterior'}
    if 'comparacio_anterior' in summary:
        execution = dict(result.estadistiques, comparacio_anterior=summary['comparacio_anterior'])
        (out/'execucio.json').write_text(json.dumps(execution, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (out/'resum.json').write_text(json.dumps(public_summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Comparació oficial amb avui i, separadament, amb el 5.2 congelat.
    escriu_csv(out/'xifres.csv', [{'xifra': k, 'abans': before_report.objectius.get(k, 0),
                                  'despres': v} for k, v in report.objectius.items()],
               ['xifra', 'abans', 'despres'])
    command = shlex.join([str(PYTHON), '-m', 'nivell2.s53', '--temps', f'{args.temps:g}', '--llavor', str(args.llavor)])
    final = RESULTATS/'5.3'
    checking = shlex.join([str(PYTHON), '-m', 'horaris', 'check', str((final/'proposta.csv').resolve()),
        '--semestre', '2', '--escenari', str(CONTINGENCIES), '--referencia', str(refpath.resolve()),
        '--relaxacions', str((final/'relaxacions.csv').resolve()), '--json', str((final/'informe.json').resolve()),
        '--violacions', str((final/'violacions.csv').resolve())])
    (out/'README.md').write_text(f'''# 5.3 Imprevistos

Veredicte oficial: **{report.veredicte}**. Incompliments no declarats: {summary['incompliments_no_declarats']}.
Reserva mínima operativa comprovada independentment: **{minimum} aules**.
Classes de suport modificades respecte del 5.2: {summary['classes_suport']}.
Estat del solver: **{result.estat}** (òptim del veïnat obert).
Temps total: {elapsed:.3f} s. Llavor: {args.llavor}. Pressupost de reparació: {args.temps:g} s.

Des del worktree:
```sh
{command}
```

Verificació oficial:
```sh
cd {shlex.quote(str(REPTE))}
{checking}
```

Comprovació de persones, des del worktree:
```sh
RESULTATS_DIR=$PWD/resultats/nivell2 {shlex.quote(str(PYTHON))} -m nivell2.comprova_persones
```

La referència i les relaxacions del 5.2 es conserven. Primer només s'obren les sessions
afectades, incloses les classes vinculades dels dobles. Si cal, s'obren veïnes,
el dia i la setmana. Cap sessió canvia de torn; només la cancel·lada canvia de dia.
Es prioritzen els canvis de franja i d'aula oficials; després, el passadís,
les hores mortes i la rutina d'aula, incloses les setmanes congelades. La cancel·lada
no compta en els canvis d'aula oficials; el recompte del CSV sí que la inclou.
Només es declara R1-FIXADA o R7-PLAB quan una aula tancada obliga a canviar
l'aula d'una sessió fixada, sense moure'n el dia ni l'hora. Els desdoblaments exigirien reservar
i comprovar també la segona meitat: aquesta reparació no els simula amb una relaxació buida.
L'estat òptim, si n'hi ha, correspon al veïnat obert, no al problema global.
`resum.json` conté només recomptes; `execucio.json` els intents i pressupostos.
La reserva exclou les aules tancades i exigeix dues aules ordinàries obertes
i lliures durant tota cada franja d'una hora, també amb classes congelades.
Una comprovació independent de la proposta final impedeix publicar si no es compleix.
La publicació exigeix OPTIMAL. També es rebutja
una proposta amb més canvis oficials totals (franja + aula) si l'anterior publicada
té una reserva mínima operativa igual o millor.
''', encoding='utf-8')
    readme = out/'README.md'
    readme.write_text(normalitza(readme.read_text(encoding='utf-8'), '5.3', RESULTATS), encoding='utf-8')
    print(report.veredicte)
    print('Canvis de franja:', summary['canvis_franja_vs_referencia'])
    print('Canvis d’aula oficials:', summary['canvis_aula_vs_referencia'])
    print('Canvis d’aula al CSV:', summary['canvis_aula_model'])
    print('Classes de suport:', summary['classes_suport'])
    print('Reserva mínima operativa:', minimum)
    if 'comparacio_anterior' in summary:
        comparison = summary['comparacio_anterior']
        for key in counts:
            print('5.3 abans/després', key+':', comparison['abans'][key], '→', counts[key])
    print('Estat solver:', result.estat)
    print('Temps determinista solver:', sum(attempt.get('diagnostic', {}).get('temps_determinista', 0)
                                            for attempt in result.estadistiques['intents']))
    for key in ('desplacaments_aula', 'r6_aules_te_extra_per_grup', 'hores_mortes_min'):
        print(key+':', before_report.objectius.get(key, 0), '→', report.objectius.get(key, 0))
    print('Sessions afectades:', summary['sessions_afectades'])
    for reason, n in summary['sessions_afectades_per_imprevist'].items():
        print(reason+':', n)
    print('Relaxacions noves:', summary['relaxacions_noves'])
    for row in resum_relaxacions(rows):
        print('Relaxacions', row['restriccio']+':', row['sessions'])
    print('Incompliments no declarats:', summary['incompliments_no_declarats'])
    print(f'Temps total: {elapsed:.3f} s')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        import traceback
        RESULTATS.mkdir(parents=True, exist_ok=True)
        (RESULTATS/'error-s53.txt').write_text(traceback.format_exc(), encoding='utf-8')
        print('Errors d’execució: 1; detall desat fora de git')
        raise SystemExit(2)

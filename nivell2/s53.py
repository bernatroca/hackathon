"""5.3: quatre contingències simultànies sobre el 5.2 congelat."""
from __future__ import annotations
from nivell2.readmes import actualitza

import argparse
import json
import shlex
import time
from collections import Counter

from nivell2.base import (CONTINGENCIES, RESULTATS, RESULTATS_PRINCIPAL,
                          PYTHON, REPTE, Proposta, carrega_model, verifica)
from nivell2.reparacio import Canvi, repara
from nivell2.s52 import escriu_csv
from horaris.model import llegeix_relaxacions


def resum_relaxacions(rows):
    """Només recomptes; no copia identificadors al resum."""
    counts = Counter()
    for r in rows:
        counts[r['restriccio'], r['justificacio']] += len(set(filter(None, r['sessions'].split('|'))))
    return [{'restriccio': rule, 'motiu': why, 'sessions': n}
            for (rule, why), n in sorted(counts.items())]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--temps', type=float, default=40)
    ap.add_argument('--llavor', type=int, default=0)
    args = ap.parse_args(argv)
    if not 0 < args.temps <= 45:
        ap.error('El pressupost ha de ser superior a zero i com a màxim de 45 segons')
    start = time.monotonic()
    out = RESULTATS/'5.3'
    out.mkdir(parents=True, exist_ok=True)
    refpath = RESULTATS_PRINCIPAL/'5.2'/'proposta.csv'
    relaxpath = refpath.parent/'relaxacions.csv'
    # Llegeixen les dades només el model i la reparació; cap fila va a stdout.
    reference = Proposta.llegeix(refpath)
    inherited = [{'restriccio': r.restriccio, 'sessions': '|'.join(sorted(r.sessions)),
                  'justificacio': r.justificacio} for r in llegeix_relaxacions(relaxpath)]
    before_report = verifica(refpath, relaxacions=relaxpath)
    if before_report.veredicte not in ('VALIDA', 'VALIDA AMB RELAXACIONS DECLARADES'):
        raise ValueError('Cal una referència 5.2 validada abans de reparar-la')
    result = repara(reference, Canvi(carrega_model(CONTINGENCIES), carrega_model(),
                                   args.temps, args.llavor))
    (out/'execucio.json').write_text(json.dumps(result.estadistiques, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if result.proposta is None:
        print('Reparació sense proposta:', result.estat, '; intents:', len(result.estadistiques['intents']))
        for attempt in result.estadistiques['intents']:
            print('Nivell:', attempt['nivell'], '; sessions obertes:', attempt['sessions_obertes'])
            for label, n in attempt.get('diagnostic', {}).items():
                print(label+':', n)
        return 1
    path = result.proposta.escriu(out/'proposta.csv')
    rows = inherited+result.relaxacions
    relax = out/'relaxacions.csv'
    escriu_csv(relax, rows, ['restriccio', 'sessions', 'justificacio'])
    report = verifica(path, escenari=CONTINGENCIES, referencia=refpath,
                      relaxacions=relax, json_path=out/'informe.json',
                      violacions_path=out/'violacions.csv')
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
    (out/'resum.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Comparació oficial amb avui i, separadament, amb el 5.2 congelat.
    escriu_csv(out/'xifres.csv', [{'xifra': k, 'abans': before_report.objectius.get(k, 0),
                                  'despres': v} for k, v in report.objectius.items()],
               ['xifra', 'abans', 'despres'])
    command = shlex.join([str(PYTHON), '-m', 'nivell2.s53', '--temps', str(args.temps), '--llavor', str(args.llavor)])
    checking = shlex.join([str(PYTHON), '-m', 'horaris', 'check', str(path.resolve()),
        '--semestre', '2', '--escenari', str(CONTINGENCIES), '--referencia', str(refpath.resolve()),
        '--relaxacions', str(relax.resolve()), '--json', str((out/'informe.json').resolve()),
        '--violacions', str((out/'violacions.csv').resolve())])
    (out/'README.md').write_text(f'''# 5.3 Imprevistos

Veredicte oficial: **{report.veredicte}**. Incompliments no declarats: {summary['incompliments_no_declarats']}.
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
Es prioritza conservar franges i aules; per recol·locar, es prefereix el mateix passadís.
Només es declara R1-FIXADA o R7-PLAB quan una aula tancada obliga a canviar
l'aula d'una sessió fixada, sense moure'n el dia ni l'hora. Els desdoblaments exigirien reservar
i comprovar també la segona meitat: aquesta reparació no els simula amb una relaxació buida.
L'estat òptim, si n'hi ha, correspon al veïnat obert, no al problema global.
`resum.json` conté només recomptes; `execucio.json` els intents i pressupostos.
''', encoding='utf-8')
    actualitza(out, '5.3')
    print(report.veredicte)
    print('Canvis de franja:', summary['canvis_franja_vs_referencia'])
    print('Canvis d’aula:', summary['canvis_aula_vs_referencia'])
    print('Sessions afectades:', summary['sessions_afectades'])
    for reason, n in summary['sessions_afectades_per_imprevist'].items():
        print(reason+':', n)
    print('Relaxacions noves:', summary['relaxacions_noves'])
    for row in resum_relaxacions(rows):
        print('Relaxacions', row['restriccio']+':', row['sessions'])
    print('Incompliments no declarats:', summary['incompliments_no_declarats'])
    print(f'Temps total: {elapsed:.3f} s')
    return 0 if report.veredicte in ('VALIDA', 'VALIDA AMB RELAXACIONS DECLARADES') and elapsed < 60 else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        import traceback
        out = RESULTATS/'5.3'
        out.mkdir(parents=True, exist_ok=True)
        (out/'error-s53.txt').write_text(traceback.format_exc(), encoding='utf-8')
        print('Errors d’execució: 1; detall desat fora de git')
        raise SystemExit(2)

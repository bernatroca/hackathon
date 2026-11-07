"""5.2 complet: franges, aules, verificador oficial i comparació."""
from __future__ import annotations
import argparse
import csv
import json
import time
from pathlib import Path

from nivell2.base import (Proposta, RESULTATS, PYTHON, REPTE, carrega_model,
                          carrega_oficial, verifica)
from nivell2.franges import assigna_franges, proposta_franges
from nivell2.aules import assigna_aules
from nivell2.xifres import compara


def escriu_csv(path, rows, columns):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def resol(base, *, temps_franges=300, temps_aules=600, llavor=0):
    """Fins a tres intents; mai retorna una proposta parcial com si fos vàlida.

    Els pressupostos són compartits entre intents de cada etapa. Un fracàs
    d'aules sense certificat es tracta com a cerca fallida, sense relaxacions.
    """
    if temps_franges <= 0 or temps_aules <= 0:
        raise ValueError('Els temps han de ser positius')
    ref = Proposta.de_base(base)
    history, limits = [], {}
    remaining_f, remaining_a = temps_franges, temps_aules
    for attempt in range(3):
        start = time.monotonic()
        slots, state_f, exceptions = assigna_franges(base, referencia=ref,
            temps_s=max(.001,remaining_f), llavor=llavor, limits_capacitat=limits, permet_excepcions_torn=True)
        elapsed_f = time.monotonic()-start
        remaining_f -= elapsed_f
        record = {'intent':attempt+1, 'franges':state_f, 'temps_franges_s':elapsed_f,
                  'limits_capacitat':dict(limits),
                  'estadistiques_franges':dict(assigna_franges.estadistiques)}
        history.append(record)
        print('Franges:',json.dumps(record,ensure_ascii=False),flush=True)
        if not slots:
            return None, exceptions, history
        start = time.monotonic()
        rooms, state_a = assigna_aules(base,slots,referencia=ref,
            temps_s=max(.001,remaining_a),llavor=llavor)
        elapsed_a = time.monotonic()-start
        remaining_a -= elapsed_a
        record.update(aules=state_a,temps_aules_s=elapsed_a)
        print('Aules:',state_a,f'{elapsed_a:.3f} s',flush=True)
        if rooms:
            proposal = proposta_franges(base,ref,slots)
            for sid,room in rooms.items():
                proposal.files[sid].aula = room
            return proposal, exceptions, history
        if remaining_f <= 0 or remaining_a <= 0:
            break
        # Necessary capacity conditions are weaker than room assignment. Tighten
        # the hourly packing by one slot in ALL buckets as a repair heuristic.
        # This is deliberately not presented as a Hall/infeasibility certificate.
        available = sum(a.tipus in ('Aules docents','Seminaris') for a in base.aules.values())-2
        limits[-1] = max(0,available-attempt-1)
        record['reintent_motiu'] = ('Aules sense solució; es redueix en una sessió la capacitat '
                                    'de tots els cubells horaris. Heurística, sense prova d’impossibilitat.')
    return None, [], history


def valida_excepcions(base, proposal, sessions):
    """Cap relaxació fora de W14, ni alternativa que no sigui la partida."""
    from nivell2.franges import _referencia
    from horaris.check import _torn_ok
    for sid in sessions:
        s = base.sessions[sid]
        if s.data.isocalendar()[:2] != (2027,14) or s.fixada:
            raise ValueError(f'Excepció R1 no autoritzada: {sid}')
        if _referencia(s,proposal) != (s.data,s.ini) or _torn_ok(s.torn,s.ini,s.fi) is not False:
            raise ValueError(f'Excepció R1 fora de la franja original: {sid}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temps-franges',type=float,default=300)
    parser.add_argument('--temps-aules',type=float,default=600)
    parser.add_argument('--llavor',type=int,default=0)
    args = parser.parse_args(argv)
    start = time.monotonic()
    out = RESULTATS/'5.2'
    out.mkdir(parents=True,exist_ok=True)
    proposal, exceptions, history = resol(carrega_model(),temps_franges=args.temps_franges,
        temps_aules=args.temps_aules,llavor=args.llavor)
    escriu_csv(out/'excepcions.csv',exceptions,
               list(exceptions[0]) if exceptions else ['id_sessio','data','minut_inici','motiu'])
    (out/'execucio.json').write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    if proposal is None:
        (out/'README.md').write_text(
            '# 5.2 pendent de solució\n\n'
            'No hi ha proposta completa ni veredicte VALIDA. Cap relaxació aplicada.\n\n'
            f'Ordre: `{PYTHON} -m nivell2.s52 --temps-franges {args.temps_franges:g} --temps-aules {args.temps_aules:g} --llavor {args.llavor}`.\n\n'
            'Estats, temps i setmana de reparació fallida: `execucio.json`.\n'
            'El diagnòstic inicial detectà tres PAUL compatibles només amb dues aules informàtiques\n'
            'coincidents el 2027-02-05 a les 15:00. Afegida la capacitat per equipament,\n'
            'la reparació de la setmana 2027-04-05 a la tarda retorna INFEASIBLE,\n'
            'també reobrint les sessions no fixades de tota aquella setmana.\n'
            'Això no és una prova d’impossibilitat del problema oficial complet: el model\n'
            'de franges inclou condicions conservadores de capacitat per cubell horari.\n'
            'No s’han generat xifres de després perquè no existeix una proposta completa.\n', encoding='utf-8')
        print('No s’ha trobat proposta completa:',json.dumps(history,ensure_ascii=False))
        return 1
    relaxed = [sid for record in history[-1:]
               for proof in record['estadistiques_franges'].get('proves_torn',[]) for sid in proof.get('sessions',[])]
    valida_excepcions(carrega_model(),proposal,relaxed)
    relax_path = out/'relaxacions.csv'
    escriu_csv(relax_path,([{'restriccio':'R1-TORN','sessions':'|'.join(sorted(relaxed)),
        'justificacio':'Setmana d’avaluació del 5 al 8 d’abril: no s’hi poden portar classes i el divendres 9 a la tarda no hi caben sense solapar docents o grups; demostrat INFEASIBLE, vegeu diagnostic.md'}] if relaxed else []),
        ['restriccio','sessions','justificacio'])
    path = proposal.escriu(out/'proposta.csv')
    report = verifica(path,json_path=out/'informe.json',violacions_path=out/'violacions.csv',relaxacions=relax_path)
    comparison = compara(proposal,base=carrega_oficial(),proposta_path=path,relaxacions=relax_path)
    escriu_csv(out/'xifres.csv',comparison.files,['xifra','abans','despres'])
    escriu_csv(out/'titulacions.csv',comparison.titulacions,list(comparison.titulacions[0]))
    (out/'diagnostic.md').write_text('# Prova de la setmana d’avaluació\n\n'
        'Del 5 al 8 d’abril no es poden portar classes d’altres dies. Les sessions que ja hi són només poden canviar d’hora el mateix dia. '
        'La resta ha de cabre el divendres 9. La combinació de disponibilitat de docents, grups i equipament impedeix fer-ho tot al torn requerit.\n\n'
        'Model de tota la setmana: totes les sessions no fixades obertes, mateixa setmana i durada, calendari, finestres, docent, alumnat, PLAB, compartides i capacitat d’equipament durs. '
        'L’única alternativa fora de torn és la franja original. Es minimitza lexicogràficament el nombre de sessions amb excepció, després els canvis.\n\n'
        + '\n'.join(f"R1 dura: {p['dur']} ({p['dur_s']:.3f} s). R1 tova: {p.get('tou')} ({p.get('tou_s',0):.3f} s), {p.get('nombre')} excepcions. "+
            ('Mínim demostrat dins del model.' if p.get('tou') == 'OPTIMAL' else 'El mínim que hem trobat, sense prova d’optimalitat.')
            for r in history for p in r['estadistiques_franges'].get('proves_torn',[]))+'\n',encoding='utf-8')
    if report.compten():
        with (out/'diagnostic.md').open('a',encoding='utf-8') as f:
            f.write('\n## Incompliments pendents després de les aules\n\n'
                + json.dumps(report.compten(),ensure_ascii=False)+'\n\n'
                'Atenció a les fixades originalment sense aula: `_marca_heretades` exigeix '
                'aula igual a l’original per eximir R1-TORN. Assignar una aula pot fer '
                'comptar el torn; deixar-la buida fa comptar R5-SENSE-AULA i moure-la '
                'fa comptar R1-FIXADA. No s’autoritzen relaxacions fora de W14.\n')
    elapsed = time.monotonic()-start
    command = f'{PYTHON} -m nivell2.s52 --temps-franges {args.temps_franges:g} --temps-aules {args.temps_aules:g} --llavor {args.llavor}'
    checking = f'{PYTHON} -m horaris check {path.resolve()} --semestre 2 --relaxacions {relax_path.resolve()} --json {out.resolve()}/informe.json --violacions {out.resolve()}/violacions.csv'
    (out/'README.md').write_text(f'''# 5.2 Torns nous

Veredicte oficial: **{report.veredicte}**. Excepcions R1-TORN: {len(relaxed)}. Temps total: {elapsed:.3f} s.
Llavor: {args.llavor}. Pressupostos: franges {args.temps_franges:g} s; aules {args.temps_aules:g} s.

Des del worktree:
```sh
{command}
```
Verificació oficial, sense `--nomes-aules`:
```sh
cd {REPTE}
{checking}
```
Proves ràpides:
```sh
{PYTHON} -m pytest nivell2/test_s52.py nivell2/test_franges.py
```

Estats i temps de cada intent:
```json
{json.dumps(history,ensure_ascii=False,indent=2)}
```

`xifres.csv` conté abans/després; `titulacions.csv` els percentatges per cohort.
`excepcions.csv` conté {len(exceptions)} excepcions de calendari amb motiu.
Les aules es resolen amb rutina prioritària, referència d'avui i reserva R8
per cubells d'una hora. B3/0021 es conserva quan no es mou la franja.
La passada opcional d'hores mortes no s'executa. No s'afirma òptim global.
Si fallen les aules, hi ha com a màxim tres intents amb capacitat horària
més estricta; aquests límits són una heurística, no una prova d'impossibilitat.
''',encoding='utf-8')
    print(report.veredicte,f'{elapsed:.3f} s')
    for row in comparison.files:
        print(f"{row['xifra']}: {row['abans']} → {row['despres']}")
    return 0 if report.veredicte in ('VALIDA','VALIDA AMB RELAXACIONS DECLARADES') else 1


if __name__ == '__main__':
    raise SystemExit(main())

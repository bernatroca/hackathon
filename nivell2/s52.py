"""5.2 complet: franges, aules, verificador oficial i comparació."""
from __future__ import annotations
import argparse
import csv
import ctypes
import os
import json
import time
import shutil
import tempfile
from pathlib import Path

from nivell2.base import (Proposta, RESULTATS, carrega_model,
                          carrega_oficial, verifica, avalua_rapid)
from nivell2.franges import assigna_franges, proposta_franges
from nivell2.aules import assigna_aules
from nivell2.xifres import compara


def escriu_csv(path, rows, columns):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def resol(base, *, temps_franges=300, temps_aules=600, llavor=0, pista=None):
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
            temps_s=max(.001,remaining_f), llavor=llavor, limits_capacitat=limits, permet_excepcions_torn=True, pista=pista)
        elapsed_f = time.monotonic()-start
        remaining_f -= elapsed_f
        record = {'intent':attempt+1, 'franges':state_f, 'temps_franges_s':elapsed_f,
                  'limits_capacitat':dict(limits),
                  'estadistiques_franges':dict(assigna_franges.estadistiques)}
        history.append(record)
        print('Franges:',state_f,f'{elapsed_f:.3f} s; sessions assignades: {len(slots)}',flush=True)
        if not slots:
            return None, exceptions, history
        start = time.monotonic()
        rooms, state_a = assigna_aules(base,slots,referencia=ref,
            temps_s=max(.001,remaining_a),llavor=llavor,pista=pista)
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
        # simultaneous packing by one slot as a repair heuristic.
        # This is deliberately not presented as a Hall/infeasibility certificate.
        available = sum(a.tipus in ('Aules docents','Seminaris') for a in base.aules.values())-2
        limits[-1] = max(0,available-attempt-1)
        record['reintent_motiu'] = ('Aules sense solució; es redueix en una sessió la capacitat '
                                    'simultània. Heurística, sense prova d’impossibilitat.')
    return None, [], history


def valida_excepcions(base, proposal, sessions):
    """Cap relaxació fora de W14, ni alternativa que no sigui la partida."""
    from nivell2.franges import _referencia
    from horaris.check import _torn_ok
    for sid in sessions:
        s = base.sessions[sid]
        if s.data.isocalendar()[:2] != (2027,14) or s.fixada:
            raise ValueError('Excepció R1 no autoritzada')
        if _referencia(s,proposal) != (s.data,s.ini) or _torn_ok(s.torn,s.ini,s.fi) is not False:
            raise ValueError('Excepció R1 fora de la franja original')


MOTIU_FIXADES = "La regla 1 diu que les classes de 1r i 2n d'aquests graus no es toquen; ja es fan a la tarda."
MOTIU_DOBLES = "El doble va a la classe d'un altre grup, que no es mou."
MOTIU_AVALUACIO = "Setmana d'avaluació: impossibilitat demostrada amb R1 dura; vegeu diagnostic.md."


def relaxacions_proposta(base, proposal, w14):
    """Només les tres decisions explícites; no declara errors desconeguts."""
    from horaris.check import _torn_ok
    from nivell2.franges import _referencia
    from nivell2.comprova_persones import parelles_dobles
    pairs,_ = parelles_dobles(base)
    frozen_hosts = set()
    for double,hosts in pairs.items():
        members = [base.sessions[sid] for sid in [double,*hosts]]
        if any(r.fixada or r.tipus == 'PLAB' for r in members):
            frozen_hosts.update(hosts)
    # Let the official inheritance rules decide which violations still count.
    # In particular unchanged doubles need no explicit relaxation.
    needed = {sid for v in avalua_rapid(base,proposal).violacions
              if v.regla == 'R1-TORN' and v.compta for sid in v.sessions}
    classified = {MOTIU_FIXADES:[],MOTIU_DOBLES:[],MOTIU_AVALUACIO:[]}
    for s in base.sessions.values():
        date,minute = _referencia(s,proposal)
        if s.id not in needed or _torn_ok(s.torn,minute,minute+s.durada) is not False:
            continue
        if (s.sense_espai or (s.id in frozen_hosts and not s.fixada)) and (date,minute) == (s.data,s.ini):
            if any(_referencia(base.sessions[p],proposal) != (base.sessions[p].data,base.sessions[p].ini)
                   for p in pairs.get(s.id,())):
                raise ValueError('Un doble fora de torn s’ha separat de la franja original')
            classified[MOTIU_DOBLES].append(s.id)
        elif s.fixada.startswith('R1') and not s.aula and (date,minute) == (s.data,s.ini):
            classified[MOTIU_FIXADES].append(s.id)
        elif s.id in w14:
            classified[MOTIU_AVALUACIO].append(s.id)
    return [{'restriccio':'R1-TORN','sessions':'|'.join(sorted(ids)),'justificacio':motiu}
            for motiu,ids in classified.items() if ids]


VALIDES = {'VALIDA','VALIDA AMB RELAXACIONS DECLARADES'}


def metriques(report):
    return {'declarats':report.json['incompliments_declarats'],
            **{k:report.objectius[k] for k in ('canvis_franja','hores_mortes_min',
                'desplacaments_aula','r6_aules_te_extra_per_grup')}}


def persones_correctes(base, proposal):
    from nivell2.comprova_persones import (colloca_avui, conflictes,
                                           parelles_dobles, comprova_dobles)
    from horaris.check import Informe as InformeIntern, _col_loca
    col = _col_loca(base,proposal.a_files(),InformeIntern())
    if set(col) != set(base.sessions):
        return False
    new = set(conflictes(col))-set(conflictes(colloca_avui(base)))
    pairs,_ = parelles_dobles(base)
    doubles = comprova_dobles(base,col,pairs)
    return not new and not any(doubles.values())


def _intercanvia(stage, out):
    """Atomic exchange on the supported macOS/Linux development systems."""
    libc = ctypes.CDLL(None,use_errno=True)
    source, target = os.fsencode(stage), os.fsencode(out)
    if hasattr(libc,'renamex_np'):
        exchange = libc.renamex_np
        exchange.argtypes = [ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint]
        exchange.restype = ctypes.c_int
        result = exchange(source,target,2)  # RENAME_SWAP on macOS
    elif hasattr(libc,'renameat2'):
        exchange = libc.renameat2
        exchange.argtypes = [ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        exchange.restype = ctypes.c_int
        result = exchange(-100,source,-100,target,2)  # RENAME_EXCHANGE
    else:
        raise OSError('El sistema no permet substituir atòmicament el lliurament')
    if result:
        code = ctypes.get_errno()
        raise OSError(code,os.strerror(code))


def publica(stage, out):
    """Publish every artifact together, with no missing-directory window."""
    if out.exists():
        _intercanvia(stage,out)
        # After the exchange, staging contains the previous complete delivery.
        shutil.rmtree(stage,ignore_errors=True)
    else:
        stage.rename(out)


def diagnostic(history, proposal_found):
    lines = ['# Diagnòstic del model 5.2', '',
        'R8 compta aules ordinàries diferents dins de cada hora. '
        'El model de franges usa només demanda simultània com a condició necessària; '
        'l’assignació d’aules imposa la unió exacta d’aules per hora. '
        'Dues classes consecutives poden ocupar la mateixa aula sense comptar dues vegades.', '',
        'L’objectiu prioritza les excepcions R1 i després aplica 10 punts per sessió '
        'amb canvi de franja i 1 punt per 30 minuts d’hora morta. '
        'La cerca continua dins del pressupost; no s’afirma òptim global.', '']
    for record in history:
        for phase in ('franges','aules'):
            state = record.get(phase)
            if state:
                meaning = ('temps esgotat sense solució; no demostra impossibilitat' if state == 'UNKNOWN'
                           else 'impossibilitat demostrada dins del model d’aquest intent' if state == 'INFEASIBLE'
                           else 'solució trobada')
                lines.append(f'{phase}: {state} — {meaning}.')
        stats = record.get('estadistiques_franges',{})
        for obstacle in stats.get('colls_capacitat',[]):
            lines.append('Recompte de classes simultànies: demanda '
                         f"{obstacle['demanda']}, oferta {obstacle['oferta']}; "
                         f"llindar d’alumnes {obstacle['mes_de_alumnes']}.")
        for proof in stats.get('proves_torn',[]):
            lines.append(f"R1 dura: {proof['dur']} ({proof['dur_s']:.3f} s). "
                         f"R1 tova: {proof.get('tou','no aplicada')}; "
                         f"excepcions: {proof.get('nombre',0)}.")
            if proof['dur'] == 'INFEASIBLE':
                lines.append('Prova de tota la setmana amb calendari, persones i equipament; '
                             'sense els límits heurístics dels reintents ni el fals recompte horari de classes.')
    if not proposal_found:
        lines += ['', 'No es publica cap proposta nova. El lliurament anterior es conserva íntegre.']
    return '\n'.join(lines)+'\n'


def _executa(args, stage, out):
    start = time.monotonic()
    previous = None
    pista = None
    if (out/'proposta.csv').exists():
        previous = verifica(out/'proposta.csv',relaxacions=(out/'relaxacions.csv')
                            if (out/'relaxacions.csv').exists() else None)
        print('Abans:',json.dumps(metriques(previous),ensure_ascii=False),flush=True)
        if previous.veredicte in VALIDES and not previous.compten():
            pista = Proposta.llegeix(out/'proposta.csv')
    base = carrega_model()
    official = carrega_oficial()
    proposal, exceptions, history = resol(base,temps_franges=args.temps_franges,
        temps_aules=args.temps_aules,llavor=args.llavor,pista=pista)
    escriu_csv(stage/'excepcions.csv',exceptions,
               list(exceptions[0]) if exceptions else ['id_sessio','data','minut_inici','motiu'])
    (stage/'execucio.json').write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    (stage/'diagnostic.md').write_text(diagnostic(history,proposal is not None),encoding='utf-8')
    if proposal is None:
        print('No s’ha trobat proposta completa; es conserva el lliurament anterior.',flush=True)
        return 1
    relaxed = [sid for record in history[-1:]
               for proof in record['estadistiques_franges'].get('proves_torn',[])
               if proof['dur'] == 'INFEASIBLE' for sid in proof.get('sessions',[])]
    valida_excepcions(base,proposal,relaxed)
    relax_path = stage/'relaxacions.csv'
    relaxations = relaxacions_proposta(official,proposal,set(relaxed))
    escriu_csv(relax_path,relaxations,['restriccio','sessions','justificacio'])
    path = proposal.escriu(stage/'proposta.csv')
    report = verifica(path,json_path=stage/'informe.json',violacions_path=stage/'violacions.csv',relaxacions=relax_path)
    print('Candidata:',report.veredicte,json.dumps(metriques(report),ensure_ascii=False),flush=True)
    cap = min(459,previous.json['incompliments_declarats']) if previous else 459
    if report.veredicte not in VALIDES or report.compten() or report.json['incompliments_declarats'] > cap:
        print('Candidata rebutjada pel veredicte o pel nombre de declarats; es conserva l’anterior.',flush=True)
        return 1
    if not persones_correctes(official,proposal):
        print('Candidata rebutjada: conflictes nous de persones o dobles separats; es conserva l’anterior.',flush=True)
        return 1
    comparison = compara(proposal,base=official,proposta_path=path,relaxacions=relax_path)
    escriu_csv(stage/'xifres.csv',comparison.files,['xifra','abans','despres'])
    escriu_csv(stage/'titulacions.csv',comparison.titulacions,list(comparison.titulacions[0]))
    elapsed = time.monotonic()-start
    counts = {**metriques(report), 'incompliments_no_declarats':sum(report.compten().values()),
        'relaxacions_fixades':sum(len(r['sessions'].split('|')) for r in relaxations if r['justificacio']==MOTIU_FIXADES),
        'relaxacions_dobles':sum(len(r['sessions'].split('|')) for r in relaxations if r['justificacio']==MOTIU_DOBLES),
        'relaxacions_avaluacio':sum(len(r['sessions'].split('|')) for r in relaxations if r['justificacio']==MOTIU_AVALUACIO)}
    (stage/'resum.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2)+'\n')
    (stage/'comparacio-lliurament.json').write_text(json.dumps(
        {'abans':metriques(previous) if previous else None,'despres':metriques(report)},ensure_ascii=False,indent=2)+'\n')
    (stage/'README.md').write_text(f'''# 5.2 Torns nous

Veredicte oficial: **{report.veredicte}**. Incompliments declarats: {report.json['incompliments_declarats']}.
Temps total: {elapsed:.3f} s. Llavor: {args.llavor}.

```sh
python -m nivell2.s52 --temps-franges {args.temps_franges:g} --temps-aules {args.temps_aules:g} --llavor {args.llavor}
python -m nivell2.verificacio 5.2
python -m nivell2.comprova_persones --resultats resultats/nivell2
```

`xifres.csv` compara amb l’horari de partida; `comparacio-lliurament.json` compara amb el lliurament anterior.
`execucio.json` registra els intents i les proves R1; `diagnostic.md` n’explica l’abast.
Les dobles heretades pel verificador no es declaren. Les excepcions R1 noves requereixen INFEASIBLE,
mai UNKNOWN, amb tota la setmana oberta i sense límits heurístics.
R8 compta aules diferents per hora. Es minimitzen canvis per sessió i hores mortes.
No s’afirma òptim global. La proposta es publica sencera després de validar-la i comprovar les persones.
''',encoding='utf-8')
    publica(stage,out)
    print(report.veredicte,f'{elapsed:.3f} s; lliurament substituït.',flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temps-franges',type=float,default=300)
    parser.add_argument('--temps-aules',type=float,default=600)
    parser.add_argument('--llavor',type=int,default=0)
    args = parser.parse_args(argv)
    # Keep failed attempts away from the directories scanned as deliveries.
    attempts = RESULTATS.parent/'.intents-s52'
    attempts.mkdir(parents=True,exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='intent-',dir=attempts))
    out = RESULTATS/'5.2'
    out.parent.mkdir(parents=True,exist_ok=True)
    try:
        return _executa(args,stage,out)
    except Exception:
        import traceback
        (stage/'error-s52.txt').write_text(traceback.format_exc(),encoding='utf-8')
        (stage/'diagnostic.md').write_text('ERROR d’execució; no és una prova d’impossibilitat. '
            'El lliurament anterior es conserva íntegre.\n',encoding='utf-8')
        print('Errors d’execució: 1; detall a la carpeta temporal. Es conserva el lliurament anterior.',flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

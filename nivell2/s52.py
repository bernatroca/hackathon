"""5.2 complet: franges, aules, verificador oficial i comparació."""
from __future__ import annotations
import argparse
import copy
import datetime as dt
from collections import Counter, defaultdict
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
from nivell2.franges import assigna_franges, proposta_franges, setmanes_avaluacio, _referencia
from nivell2.aules import assigna_aules
from nivell2.xifres import compara


def escriu_csv(path, rows, columns):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def resol(base, *, temps_franges=300, temps_aules=600, llavor=0, pista=None):
    """Fins a tres intents; mai retorna una proposta parcial com si fos vàlida.

    Amb una pista verificada només es restaura localment, sense solvers globals.
    Els pressupostos són compartits entre intents de cada etapa. Un fracàs
    d'aules sense certificat es tracta com a cerca fallida, sense relaxacions.
    """
    if temps_franges <= 0 or temps_aules <= 0:
        raise ValueError('Els temps han de ser positius')
    if pista is not None:
        # Una pista vàlida ja té aules: només es restaura la rutina localment.
        return copy.deepcopy(pista), [], [{'intent':1, 'mode':'restauracio_local',
            'estadistiques_franges':{'pista_verificada':True}}]
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


def valida_excepcions(base, proposal, sessions, *, setmanes=None):
    """Cap relaxació fora de l’avaluació, ni alternativa aliena a la partida."""
    setmanes = setmanes_avaluacio() if setmanes is None else setmanes
    from nivell2.franges import _referencia
    from horaris.check import _torn_ok
    for sid in sessions:
        s = base.sessions[sid]
        if s.data-dt.timedelta(days=s.data.weekday()) not in setmanes or s.fixada:
            raise ValueError('Excepció R1 no autoritzada')
        if _referencia(s,proposal) != (s.data,s.ini) or _torn_ok(s.torn,s.ini,s.fi) is not False:
            raise ValueError('Excepció R1 fora de la franja original')


MOTIU_FIXADES = "La regla 1 diu que les classes de 1r i 2n d'aquests graus no es toquen; ja es fan a la tarda."
MOTIU_DOBLES = "El doble va a la classe d'un altre grup, que no es mou."
MOTIU_AVALUACIO = "Setmana d'avaluació: impossibilitat demostrada amb R1 dura; vegeu diagnostic.md."


def relaxacions_proposta(base, proposal, avaluacio):
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
        elif s.id in avaluacio:
            classified[MOTIU_AVALUACIO].append(s.id)
    return [{'restriccio':'R1-TORN','sessions':'|'.join(sorted(ids)),'justificacio':motiu}
            for motiu,ids in classified.items() if ids]


VALIDES = {'VALIDA','VALIDA AMB RELAXACIONS DECLARADES'}


def metriques(report, proposal=None, base=None):
    routine = {'excepcions_rutina': len(excepcions_rutina(base, proposal))} if proposal is not None else {}
    return {**report.json.get('objectius',{}), **routine,
            'declarats':report.json['incompliments_declarats'],
            **{k:report.json.get('objectius', {}).get(k, 0) for k in ('canvis_franja','hores_mortes_min',
                'desplacaments_aula','desplacaments_edifici','r6_aules_te_extra_per_grup')}}


def persones_correctes(base, proposal):
    from nivell2.comprova_persones import (colloca_avui, conflictes,
                                           parelles_dobles, comprova_dobles, conflictes_docents)
    from horaris.check import Informe as InformeIntern, _col_loca
    col = _col_loca(base,proposal.a_files(),InformeIntern())
    if set(col) != set(base.sessions):
        return False
    original = colloca_avui(base)
    new = ((set(conflictes(col))-set(conflictes(original))) |
           (set(conflictes_docents(col))-set(conflictes_docents(original))))
    pairs,_ = parelles_dobles(base)
    doubles = comprova_dobles(base,col,pairs)
    return not new and not any(doubles.values())


def patrons_rutina(base, proposal):
    """Patró modal conjunt dia/hora/aula; desempats deterministes."""
    patterns = defaultdict(Counter)
    for sid, row in base.sessions.items():
        date, minute = _referencia(row, proposal)
        patterns[row.activitat or sid][date.weekday(), minute, proposal.files[sid].aula] += 1
    return {a: min(c, key=lambda v: (-c[v], v)) for a,c in patterns.items()}


def excepcions_rutina(base, proposal):
    patterns = patrons_rutina(base, proposal)
    return {sid: patterns[row.activitat or sid] for sid,row in base.sessions.items()
            if (_referencia(row, proposal)[0].weekday(), _referencia(row, proposal)[1],
                proposal.files[sid].aula) != patterns[row.activitat or sid]}


def qualitat_rutina(base, proposal):
    exceptions = excepcions_rutina(base, proposal)
    deviations = 0
    for sid, pattern in exceptions.items():
        date, minute = _referencia(base.sessions[sid], proposal)
        actual = date.weekday(), minute, proposal.files[sid].aula
        deviations += sum(a != b for a,b in zip(actual, pattern))
    return len(exceptions), deviations


def restaura_conjunt(base, initial, variant):
    """Aplica una restauració conjunta indicada per una variant verificable.

    La variant només pot portar sessions al patró de main; totes les altres
    cel·les es conserven. No importa identificadors ni recomptes concrets.
    """
    if set(variant.files) != set(initial.files):
        raise ValueError('La variant té sessions diferents de la pista')
    patterns = patrons_rutina(base, initial)
    candidate = copy.deepcopy(initial)
    for sid,row in base.sessions.items():
        old, new = _referencia(row,initial), _referencia(row,variant)
        if old == new:
            if initial.files[sid].aula != variant.files[sid].aula:
                raise ValueError('La variant canvia una aula sense moure la sessió')
            continue
        if (new[0].weekday(),new[1]) != patterns[row.activitat or sid][:2]:
            raise ValueError('La variant mou una sessió fora del patró de la pista')
        candidate.files[sid] = copy.deepcopy(variant.files[sid])
    return candidate


def qualitat_protegida(before, after):
    """Cap +1 d'aula TE extra ni més d'un 2 % de desplaçaments d'aula."""
    return (after['desplacaments_aula']*100 <= before['desplacaments_aula']*102
            and after['r6_aules_te_extra_per_grup'] < before['r6_aules_te_extra_per_grup']+1)


def aules_locals(base, current, candidate, moved):
    """Repara només aules de sessions mogudes; obstacles del mateix dia fixos."""
    dates = {_referencia(base.sessions[sid], candidate)[0] for sid in moved}
    sub = copy.copy(base)
    sub.sessions = {sid:row for sid,row in base.sessions.items()
                    if _referencia(row, candidate)[0] in dates}
    sub.ordre = [sid for sid in base.ordre if sid in sub.sessions]
    slots = {sid:_referencia(row, candidate) for sid,row in sub.sessions.items()}
    rooms,_ = assigna_aules(sub, slots, referencia=current, pista=candidate,
                           fixes=set(sub.sessions)-set(moved), temps_s=5)
    if not rooms:
        return None
    result = copy.deepcopy(candidate)
    for sid in moved:
        result.files[sid].aula = rooms[sid]
    return result


def restaura_rutina(base, proposal, relaxacions, stage, report=None, *, limits=None):
    """Descens estricte de les excepcions, validant oficialment cada canvi.

    Les classes físiques i els vincles del doble es proven conjuntament.
    Es conserva cada aula mentre no es mogui la sessió. Primer l'aula actual;
    després la modal i, si hi ha conflictes d'aula, una reparació del dia.
    Els motius són els rebuigs reals de l'última passada sense millora.
    """
    from nivell2.base import fmt
    from horaris.model import DIES
    from nivell2.comprova_persones import parelles_dobles
    path = stage/'restauracio-temporal.csv'
    current = copy.deepcopy(proposal)
    report = report or verifica(current.escriu(path), relaxacions=relaxacions)
    if report.veredicte not in VALIDES or report.compten() or not persones_correctes(base, current):
        return current, report, []
    protected = metriques(report)
    parent = {sid:sid for sid in base.sessions}
    def root(sid):
        while parent[sid] != sid:
            parent[sid] = parent[parent[sid]]
            sid = parent[sid]
        return sid
    units = defaultdict(list)
    for row in base.sessions.values():
        units[row.unitat].append(row.id)
    pairs,_ = parelles_dobles(base)
    for ids in [*units.values(), *([sid,*hosts] for sid,hosts in pairs.items())]:
        for sid in ids[1:]:
            parent[root(sid)] = root(ids[0])
    components = defaultdict(list)
    for sid in parent:
        components[root(sid)].append(sid)
    restored = 0
    while True:
        exceptions = excepcions_rutina(base, current)
        patterns = patrons_rutina(base, current)
        reasons, improved, seen = {}, False, set()
        for sid in sorted(exceptions):
            exceptions = excepcions_rutina(base, current)
            patterns = patrons_rutina(base, current)
            if sid not in exceptions:
                continue
            key = root(sid)
            if key in seen:
                continue
            seen.add(key)
            members = components[key]
            failures, attempted = [], set()
            room_failure = False
            time_candidate = None
            moved = set()
            for modal_room in (False, True, None):
                if modal_room is None:
                    if not room_failure or not moved:
                        continue
                    candidate = aules_locals(base, current, time_candidate, moved)
                    if candidate is None:
                        failures.append('cap aula trobada per a les sessions mogudes amb la resta fixada')
                        continue
                else:
                    candidate = copy.deepcopy(current)
                    moved = set()
                    for member in members:
                        row = base.sessions[member]
                        day, minute, room = patterns[row.activitat or member]
                        assignment = candidate.files[member]
                        assignment.dia, assignment.h_ini = DIES[day], fmt(minute)
                        if assignment.data:
                            monday = row.data-dt.timedelta(days=row.data.weekday())
                            assignment.data = (monday+dt.timedelta(days=day)).isoformat()
                        if _referencia(row, candidate) != _referencia(row, current):
                            moved.add(member)
                            if modal_room:
                                assignment.aula = room
                    if not modal_room:
                        time_candidate = candidate
                signature = tuple((member, candidate.files[member].dia,
                    candidate.files[member].h_ini, candidate.files[member].aula,
                    candidate.files[member].data) for member in members)
                if signature in attempted:
                    continue
                attempted.add(signature)
                if candidate == current:
                    failures.append('aula conservada: la sessió no canvia de dia ni d’hora')
                    continue
                result = verifica(candidate.escriu(path), relaxacions=relaxacions)
                failed = []
                if result.veredicte not in VALIDES or result.compten():
                    failed.append('restriccions oficials: '+', '.join(sorted(result.compten())))
                    room_failure |= bool(result.compten()) and set(result.compten()) <= {
                        'R3-AFORAMENT','R4-AULA','R5-TIPUS','R8-RESERVA'}
                if result.json['incompliments_declarats'] > report.json['incompliments_declarats']:
                    failed.append('augment dels incompliments declarats')
                if not failed and not persones_correctes(base, candidate):
                    failed.append('conflictes nous de persones o vincle de doble separat/duplicat')
                metrics = metriques(result)
                if not qualitat_protegida(protected, metrics):
                    failed.append('empitjora desplaçaments d’aula més del 2 % o afegeix una aula TE extra')
                if limits is not None:
                    now = metriques(report)
                    if any(metrics[k] > max(now[k], limits[k]) for k in limits
                           if k != 'excepcions_rutina'):
                        failed.append('supera el límit de qualitat de la variant de referència')
                if qualitat_rutina(base, candidate) >= qualitat_rutina(base, current):
                    failed.append('no millora la rutina (excepcions i desviacions de dia/hora/aula)')
                if not failed:
                    restored += len(exceptions)-len(excepcions_rutina(base, candidate))
                    current, report, improved = candidate, result, True
                    break
                failures.extend(failed)
            for member in members:
                if member in exceptions:
                    reasons[member] = ('Restauració al patró rebutjada: '+
                        '; '.join(dict.fromkeys(failures)) if failures else
                        'Vincle de classe física: els patrons de les activitats vinculades són incompatibles.')
        if not improved:
            break
    notes = []
    for sid in sorted(excepcions_rutina(base, current)):
        date, minute = _referencia(base.sessions[sid], current)
        notes.append({'id_sessio':sid, 'data':date.isoformat(), 'minut_inici':minute,
                      'motiu':reasons[sid]})
    path.unlink(missing_ok=True)
    print('Restauració de rutina: excepcions eliminades:', restored,
          '; excepcions restants:', len(notes), flush=True)
    return current, report, notes


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
        'L’objectiu prioritza les excepcions R1, després la rutina per activitat/setmana, i després aplica 10 punts per sessió '
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
    source = getattr(args, 'origen', None) or out/'proposta.csv'
    source = Path(source)
    if getattr(args, 'origen', None) and not source.is_file():
        raise ValueError('No existeix el CSV d’origen')
    source_relax = source.with_name('relaxacions-pista-inicial.csv'
                                    if source.name == 'pista-inicial.csv' else 'relaxacions.csv')
    if source.exists():
        previous = verifica(source,relaxacions=source_relax if source_relax.exists() else None)
        if previous.veredicte in VALIDES and not previous.compten():
            # Còpia de main dins del lliurament, abans de qualsevol restauració.
            shutil.copyfile(source, stage/'pista-inicial.csv')
            pista = Proposta.llegeix(stage/'pista-inicial.csv')
            if source_relax.exists():
                shutil.copyfile(source_relax, stage/'relaxacions-pista-inicial.csv')
            prior_diagnostic = source.with_name('diagnostic.md')
            if prior_diagnostic.exists():
                shutil.copyfile(prior_diagnostic,stage/'diagnostic-pista.md')
        elif getattr(args, 'origen', None):
            raise ValueError('La proposta d’origen no és vàlida')
    base = carrega_model()
    official = carrega_oficial()
    before = metriques(previous, pista, official) if pista is not None else None
    limits = None
    variant_path = getattr(args, 'referencia_qualitat', None)
    if variant_path:
        if pista is None:
            raise ValueError('La variant de qualitat requereix una pista verificada')
        variant = Proposta.llegeix(variant_path)
        variant_report = verifica(variant_path,relaxacions=source_relax if source_relax.exists() else None)
        if (variant_report.veredicte not in VALIDES or variant_report.compten()
                or not persones_correctes(official, variant)):
            raise ValueError('La variant de referència no és vàlida')
        limits = metriques(variant_report,variant,official)
        shutil.copyfile(variant_path,stage/'variant-referencia.csv')
        print('Variant:',json.dumps(limits,ensure_ascii=False),flush=True)
    if before:
        print('Abans:', json.dumps(before,ensure_ascii=False),flush=True)
    proposal, exceptions, history = resol(base,temps_franges=args.temps_franges,
        temps_aules=args.temps_aules,llavor=args.llavor,pista=pista)
    escriu_csv(stage/'excepcions.csv',exceptions,
               list(exceptions[0]) if exceptions else ['id_sessio','data','minut_inici','motiu'])
    (stage/'execucio.json').write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    (stage/'diagnostic.md').write_text(diagnostic(history,proposal is not None),encoding='utf-8')
    if proposal is None:
        print('No s’ha trobat proposta completa; es conserva el lliurament anterior.',flush=True)
        return 1
    relax_path = stage/'relaxacions.csv'
    if pista is not None:
        if source_relax.exists():
            shutil.copyfile(source_relax,relax_path)
            with relax_path.open(encoding='utf-8-sig',newline='') as stream:
                relaxations = list(csv.DictReader(stream))
        else:
            relaxations = []
            escriu_csv(relax_path,relaxations,['restriccio','sessions','justificacio'])
        with (stage/'diagnostic.md').open('a',encoding='utf-8') as stream:
            stream.write('\nRestauració local d’una proposta prèviament verificada; no es resolen '
                         'franges ni aules de tot el semestre. Les relaxacions es conserven de la pista; '
                         'la seva justificació anterior es conserva a diagnostic-pista.md si estava disponible.\n')
    else:
        relaxed = [sid for record in history[-1:]
                   for proof in record['estadistiques_franges'].get('proves_torn',[])
                   if proof['dur'] == 'INFEASIBLE' for sid in proof.get('sessions',[])]
        valida_excepcions(base,proposal,relaxed)
        relaxations = relaxacions_proposta(official,proposal,set(relaxed))
        escriu_csv(relax_path,relaxations,['restriccio','sessions','justificacio'])
    if limits is not None:
        proposal = restaura_conjunt(official,proposal,variant)
        history.append({'mode':'restauracio_conjunta_verificada',
                        'sessions_mogudes':sum(_referencia(row,proposal) != _referencia(row,pista)
                                              for row in official.sessions.values()),
                        'estadistiques_franges':{}})
        (stage/'execucio.json').write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    path = proposal.escriu(stage/'proposta.csv')
    report = verifica(path,json_path=stage/'informe.json',violacions_path=stage/'violacions.csv',relaxacions=relax_path)
    cap = previous.json['incompliments_declarats'] if previous else sum(
        len(r['sessions'].split('|')) for r in relaxations)
    if report.veredicte in VALIDES and not report.compten() and report.json['incompliments_declarats'] <= cap:
        proposal, report, exceptions = restaura_rutina(official,proposal,relax_path,stage,report,limits=limits)
        proposal.escriu(path)
        escriu_csv(stage/'excepcions.csv',exceptions,['id_sessio','data','minut_inici','motiu'])
        report = verifica(path,json_path=stage/'informe.json',violacions_path=stage/'violacions.csv',relaxacions=relax_path)
    after = metriques(report,proposal,official)
    print('Candidata:',report.veredicte,json.dumps(after,ensure_ascii=False),flush=True)
    if (report.veredicte != 'VALIDA AMB RELAXACIONS DECLARADES' or report.compten()
            or report.json['incompliments_declarats'] > cap
            or (before is not None and after['excepcions_rutina'] >= before['excepcions_rutina'])
            or (before is not None and not qualitat_protegida(before, after))
            or (limits is not None and any(after[k] > limits[k] for k in limits))):
        print('Candidata rebutjada pel veredicte, declarats, rutina o proteccions de qualitat; es conserva l’anterior.',flush=True)
        return 1
    if not persones_correctes(official,proposal):
        print('Candidata rebutjada: conflictes nous de persones o dobles separats; es conserva l’anterior.',flush=True)
        return 1
    comparison = compara(proposal,base=official,proposta_path=path,relaxacions=relax_path)
    escriu_csv(stage/'xifres.csv',comparison.files,['xifra','abans','despres'])
    escriu_csv(stage/'titulacions.csv',comparison.titulacions,list(comparison.titulacions[0]))
    if pista is not None:
        unchanged_room_changes = sum(
            proposal.files[sid].aula != pista.files[sid].aula
            and _referencia(row,proposal) == _referencia(row,pista)
            for sid,row in official.sessions.items())
        if unchanged_room_changes:
            print('Candidata rebutjada: aules canviades sense moure la sessió:',unchanged_room_changes,flush=True)
            return 1
        print('Aules canviades sense moure la sessió:',unchanged_room_changes,flush=True)
    elapsed = time.monotonic()-start
    counts = {**after, 'incompliments_no_declarats':sum(report.compten().values()),
        'relaxacions_fixades':sum(len(r['sessions'].split('|')) for r in relaxations if r['justificacio']==MOTIU_FIXADES),
        'relaxacions_dobles':sum(len(r['sessions'].split('|')) for r in relaxations if r['justificacio']==MOTIU_DOBLES),
        'relaxacions_avaluacio':sum(len(r['sessions'].split('|')) for r in relaxations if r['justificacio']==MOTIU_AVALUACIO)}
    (stage/'resum.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2)+'\n')
    (stage/'comparacio-lliurament.json').write_text(json.dumps(
        {'abans':before,'variant':limits,'despres':after},ensure_ascii=False,indent=2)+'\n')
    quality_option = (' --referencia-qualitat resultats/nivell2/5.2/variant-referencia.csv'
                      if limits is not None else '')
    table = '\n'.join(f"| {name} | {before.get(key, '—') if before else '—'} | {after[key]} |"
        for name,key in [('Excepcions de rutina','excepcions_rutina'),('Canvis de franja','canvis_franja'),
                         ('Hores mortes (min)','hores_mortes_min'),('Desplaçaments d’aula','desplacaments_aula'),
                         ('Desplaçaments d’edifici','desplacaments_edifici'),('Declarats','declarats')])
    cost_note = ('La restauració és local i conserva les aules de les sessions no mogudes. '
                 'Els canvis de franja i d’hores mortes provenen de tornar les sessions al patró; '
                 'no es demostra que aquest cost sigui mínim ni inevitable.')
    (stage/'README.md').write_text(f'''# 5.2 Torns nous

Veredicte oficial: **{report.veredicte}**. Incompliments declarats: {report.json['incompliments_declarats']}.
Temps total: {elapsed:.3f} s. Llavor: {args.llavor}.

```sh
python -m nivell2.s52 --origen resultats/nivell2/5.2/pista-inicial.csv{quality_option} --temps-franges {args.temps_franges:g} --temps-aules {args.temps_aules:g} --llavor {args.llavor}
python -m nivell2.verificacio 5.2
python -m nivell2.comprova_persones --resultats resultats/nivell2
```

`xifres.csv` compara amb l’horari de partida; `comparacio-lliurament.json` compara amb el lliurament anterior.
`execucio.json` registra els intents i les proves R1; `diagnostic.md` n’explica l’abast.
Les dobles heretades pel verificador no es declaren. Les excepcions R1 noves requereixen INFEASIBLE,
mai UNKNOWN, amb tota la setmana oberta i sense límits heurístics.
**Reproducció (B4): aquest lliurament parteix del 5.2 anterior verificat,
copiat a `pista-inicial.csv`, amb les relaxacions a `relaxacions-pista-inicial.csv`.
Si s’utilitza una variant validada per a restauracions conjuntes, es conserva a `variant-referencia.csv`.
No es pot reproduir des de zero amb aquesta ordre ni només amb la llavor. Cal conservar
el CSV de partida i les seves relaxacions, a més de les dades i la versió del codi.**
R8 compta aules diferents per hora. Es conserven les aules de totes les sessions no mogudes.
Amb una pista vàlida no es torna a executar l’assignació global de franges ni d’aules.
Es rebutja una candidata amb més d’un 2 % de desplaçaments addicionals o +1 aula TE extra.
La passada final prova de restaurar cada excepció i verifica oficialment cada canvi acceptat.
`excepcions.csv` inclou totes les sessions encara fora del patró i el rebuig real de restaurar-les.

| Xifra | Abans | Després |
|---|---:|---:|
{table}

{cost_note}

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
    parser.add_argument('--origen',type=Path,help='CSV verificat de partida; només restauració local')
    parser.add_argument('--referencia-qualitat',type=Path,help='variant que no es pot empitjorar en cap mètrica')
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

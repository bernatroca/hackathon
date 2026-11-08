"""5.4: grau nou sobre el 5.2, amb rutina i sense desdoblaments.

Les dades només les llegeix aquest solver. La consola només mostra recomptes.
Un INFEASIBLE amb el 5.2 congelat és resposta 2, mai resposta 4.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import itertools
import json
import re
import shutil
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from nivell2.base import (ARREL, GRAU_NOU, PYTHON, RESULTATS,
                          Proposta, carrega_model, carrega_oficial, verifica)
from nivell2.franges import _candidats, _referencia, _regles, _setmana
from nivell2.franges import _hores_mortes
from nivell2.alumnat import ReglaAlumnat
from nivell2.s52 import escriu_csv
from nivell2.readmes import explica_comptatge, NOTA_GRAU_NOU, conserva_seccions
from nivell2.xifres_lliurament import comptatge_verificador
from nivell2.comprova_persones import (colloca_avui, comprova_dobles, conflictes, conflictes_docents,
                                      parelles_dobles)
from horaris.check import (FRANGES, RESERVA_MIN, Informe as InformeIntern,
                           _col_loca, _espai_ok, avalua)
from horaris.model import DIES, MATI, a_traslladar, fmt, llegeix_relaxacions


VALIDES = {'VALIDA', 'VALIDA AMB RELAXACIONS DECLARADES'}


def referencia_completa(base, referencia):
    """Afegeix les sessions noves sense alterar cap fila del 5.2."""
    if not set(referencia.files) <= set(base.sessions):
        raise ValueError('La referència conté sessions alienes a l’escenari')
    p = Proposta.de_base(base)
    p.files.update(copy.deepcopy(referencia.files))
    return p


def _activitats(base, noves):
    """Rutines també si l'escenari no porta activitat_id (mai una per fila).

    La definició d'activitat de l'especificació és grup, dia i hora recurrents.
    Sense identificador, es reconstrueix amb assignatura, tipus, grup i franja
    original. Dues classes setmanals del mateix grup continuen sent diferents.
    """
    def key(s):
        return ('activitat', s.activitat) if s.activitat else (
            'inferida', s.codi, s.tipus, s.grup, s.dia, s.ini, s.durada)

    parent = {key(base.sessions[s]): key(base.sessions[s]) for s in noves}

    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    units = defaultdict(list)
    for sid in sorted(noves):
        units[base.sessions[sid].unitat].append(base.sessions[sid])
    for rows in units.values():
        for s in rows[1:]:
            parent[root(key(s))] = root(key(rows[0]))
    acts = defaultdict(list)
    for sid in sorted(noves):
        s = base.sessions[sid]
        acts[root(key(s))].append(s)
    return list(acts.values())


def _solapa(a, b, c, d):
    return a < d and c < b


def _objectiu(model, base, acts, slots, roomvars, options, regla):
    """Ordre lexicogràfic exacte: canvis de franja, minuts morts, aules.

    El 5.2 té cost zero provat perquè està congelat. Les cotes de cada
    nivell fan que cap millora inferior compensi una sessió nova moguda.
    Les agendes conserven les línies i els subgrups del verificador.
    """
    moves = []
    for a, rows in enumerate(acts):
        for s in rows:
            moved = model.new_bool_var('nova_fora_franja')
            original = DIES.index(s.dia)*1440+s.ini
            model.add(slots[a] != original).only_enforce_if(moved)
            model.add(slots[a] == original).only_enforce_if(moved.Not())
            moves.append(moved)
    units, starts, weeks = defaultdict(list), {}, defaultdict(list)
    for a, rows in enumerate(acts):
        for s in rows:
            units[s.unitat].append(s)
            starts[s.unitat] = slots[a]
    # _hores_mortes itera conjunts: claus enteres estables eviten que el
    # hash aleatori dels identificadors alteri l'ordre de creació de variables.
    keys = sorted(units, key=lambda u: min(s.id for s in units[u]))
    units = {i: units[u] for i, u in enumerate(keys)}
    starts = {i: starts[u] for i, u in enumerate(keys)}
    for u, rows in units.items():
        weeks[_setmana(rows[0])].append(u)
    gaps = _hores_mortes(model, base, units, starts, weeks)
    # Aula base per cohort/línia: nombre d'aules diferents al llarg de tot
    # el semestre. També penalitzem parelles d'activitats del grup que
    # comparteixen dia però no aula (inclou les classes consecutives).
    groups = defaultdict(set)
    for a, rows in enumerate(acts):
        for s in rows:
            for c in s.cohorts:
                groups[c, '*' if len(regla.teories[c]) == 1 else s.linia].add(a)
    room_cost = []
    for members in groups.values():
        for r in sorted({r for a in members for _, r in options[a]}):
            uses = []
            for a in sorted(members):
                use = model.new_bool_var('aula_base')
                model.add(roomvars[a] == r).only_enforce_if(use)
                model.add(roomvars[a] != r).only_enforce_if(use.Not())
                uses.append(use)
            used = model.new_bool_var('aula_del_grup')
            model.add_max_equality(used, uses)
            room_cost.append(used)
        for a, b in itertools.combinations(sorted(members), 2):
            days = [model.new_int_var(0, 4, 'dia_canvi_aula') for _ in range(2)]
            for day, slot in zip(days, (slots[a], slots[b])):
                model.add_division_equality(day, slot, 1440)
            same = model.new_bool_var('mateix_dia_aula')
            model.add(days[0] == days[1]).only_enforce_if(same)
            model.add(days[0] != days[1]).only_enforce_if(same.Not())
            diff = model.new_bool_var('canvi_aula_grup')
            model.add(roomvars[a] != roomvars[b]).only_enforce_if(diff)
            model.add(roomvars[a] == roomvars[b]).only_enforce_if(diff.Not())
            cost = model.new_bool_var('penalitzacio_aula')
            model.add_min_equality(cost, [same, diff])
            room_cost.append(cost)
    room_bound = len(room_cost)
    lower_bound = len(gaps)*1440*(room_bound+1)+room_bound
    model.minimize(sum(moves)*(lower_bound+1) + sum(gaps)*(room_bound+1) + sum(room_cost))
    return moves, gaps, room_cost


def resol_congelat(base, referencia, *, temps_s=60, llavor=0):
    """Model conjunt exacte dins les condicions: rutina dura i 5.2 congelat.

    Una opció és (dia, hora, aula) per a totes les setmanes d'una activitat.
    Es comproven dates reals, aforament sumat de compartides, tipus, tancaments,
    aula, docent, alumnat, PLAB i la unió d'aules per cubell R8 d'una hora.
    Cap retall heurístic de capacitat ni exempció nova.
    """
    if temps_s <= 0:
        raise ValueError('El temps ha de ser positiu')
    begin = time.monotonic()
    ref = referencia_completa(base, referencia)
    noves = set(base.sessions) - set(referencia.files)
    if not noves:
        raise ValueError('L’escenari no afegeix sessions')
    if any(base.sessions[s].fixada or base.sessions[s].aula or
           base.sessions[s].sense_espai or base.sessions[s].torn != 'mati' for s in noves):
        raise ValueError('Les sessions noves han de ser movibles, de matí i sense aula')
    acts = _activitats(base, noves)
    regla = ReglaAlumnat(base.sessions.values())

    def regles(a, b):
        return _regles(a, b) or regla(a, b)
    fixed = defaultdict(list)
    occupied = defaultdict(set)
    ordinary = {a for a, room in base.aules.items() if room.ordinaria}
    for sid in referencia.files:
        s = base.sessions[sid]
        date, start = _referencia(s, ref)
        room = ref.files[sid].aula
        fixed[date].append((s, start, start+s.durada, room))
        if room in ordinary and not s.sense_espai:
            for f in FRANGES:
                if _solapa(start, start+s.durada, f, f+60):
                    occupied[date, f].add(room)
    rooms = sorted(base.aules)
    rid = {r: i for i, r in enumerate(rooms)}
    options, rejected = [], Counter()
    diagnostics = []
    for rows in acts:
        domain = set.intersection(*(set(_candidats(base, s, ref, {})) for s in rows))
        # Dues classes físiques de la mateixa setmana no poden tenir el
        # mateix dia, hora i aula. No es fusionen ni es desdoblen.
        week_units = defaultdict(set)
        for s in rows:
            week_units[_setmana(s)].add(s.unitat)
        if any(len(us) > 1 for us in week_units.values()):
            domain.clear()
        eligible = {a for a in rooms if not a_traslladar(a) and a != 'B3/0021'
                    and all(_espai_ok(base, s, a) for s in rows)}
        units = defaultdict(list)
        for s in rows:
            units[s.unitat].append(s)
        size = max(sum(s.alumnes for s in ss) for ss in units.values())
        eligible = {a for a in eligible if base.aules[a].capacitat >= size}
        allowed = []
        for slot in sorted(domain):
            dates = [(_setmana(s)+dt.timedelta(days=slot//1440), s) for s in rows]
            start = slot % 1440
            if any(s.unitat != other.unitat and regles(s, other)
                   and _solapa(start, start+s.durada, t, end)
                   for date, s in dates for other, t, end, _ in fixed[date]):
                rejected['persones_o_plab'] += 1
                continue
            blocked_rooms = {oldroom for date, s in dates for other, t, end, oldroom in fixed[date]
                             if not other.sense_espai and other.unitat != s.unitat
                             and _solapa(start, start+s.durada, t, end)}
            for room in sorted(eligible):
                if room in blocked_rooms:
                    rejected['aula_ocupada'] += 1
                    continue
                if any(t.aula == room and t.data_ini <= date <= t.data_fi
                       and _solapa(start, start+s.durada, t.ini, t.fi)
                       for date, s in dates for t in base.tancaments):
                    rejected['aula_tancada'] += 1
                    continue
                if len(ordinary) >= RESERVA_MIN and room in ordinary and any(
                        room not in occupied[date, f]
                        and len(occupied[date, f]) >= len(ordinary)-RESERVA_MIN
                        for date, s in dates for f in FRANGES
                        if _solapa(start, start+s.durada, f, f+60)):
                    rejected['reserva'] += 1
                    continue
                allowed.append((slot, rid[room]))
        options.append(allowed)
        diagnostics.append({'sessions': [s.id for s in rows], 'franges_calendari': len(domain),
                            'aules_compatibles': len(eligible), 'opcions': len(allowed)})
    stats = {'condicions': 'rutina obligatòria; 5.2 congelat; mateix torn; sense desdoblaments',
             'sessions_noves': len(noves), 'activitats_noves': len(acts),
             'sessions_noves_amb_activitat_id': sum(bool(base.sessions[s].activitat) for s in noves),
             'opcions_per_activitat': [len(o) for o in options],
             'rebuigs': dict(rejected), 'diagnostic_activitats': diagnostics}
    if any(not o for o in options):
        stats.update(estat='INFEASIBLE', causa='domini_buit', temps_s=time.monotonic()-begin)
        return None, stats
    stats['temps_candidats_s'] = time.monotonic()-begin
    model = cp_model.CpModel()
    slots, roomvars = [], []
    for opts in options:
        slot = model.new_int_var_from_domain(cp_model.Domain.from_values(sorted({s for s, _ in opts})), 'franja')
        room = model.new_int_var_from_domain(cp_model.Domain.from_values(sorted({r for _, r in opts})), 'aula')
        model.add_allowed_assignments([slot, room], opts)
        slots.append(slot)
        roomvars.append(room)
    for a, b in itertools.combinations(range(len(acts)), 2):
        durations = set()
        for s in acts[a]:
            for t in acts[b]:
                if _setmana(s) == _setmana(t):
                    if s.unitat != t.unitat:
                        durations.add((s.durada, t.durada, bool(regles(s, t))))
        for da, db, people in sorted(durations):
            before = model.new_bool_var('abans')
            after = model.new_bool_var('despres')
            model.add(slots[a]+da <= slots[b]).only_enforce_if(before)
            model.add(slots[b]+db <= slots[a]).only_enforce_if(after)
            alternatives = [before, after]
            if not people:
                different = model.new_bool_var('aules_diferents')
                model.add(roomvars[a] != roomvars[b]).only_enforce_if(different)
                alternatives.append(different)
            model.add_bool_or(alternatives)
    # R8 compta aules diferents, també quan dues classes consecutives en
    # comparteixen una dins del mateix cubell. No comptem classes simultànies.
    usage = defaultdict(lambda: defaultdict(set))
    if len(ordinary) >= RESERVA_MIN:
        for a, opts in enumerate(options):
            for slot, r in opts:
                room = rooms[r]
                if room not in ordinary:
                    continue
                for s in acts[a]:
                    date = _setmana(s)+dt.timedelta(days=slot//1440)
                    for f in FRANGES:
                        if room not in occupied[date, f] and _solapa(slot%1440, slot%1440+s.durada, f, f+60):
                            usage[date, f, r][a].add(slot)
    cache = {}

    def member(a, room, values):
        key = a, room, tuple(sorted(values))
        if key not in cache:
            lit = model.new_bool_var('ocupa_cubell')
            in_slot = model.new_bool_var('franja_del_cubell')
            model.add_linear_expression_in_domain(slots[a], cp_model.Domain.from_values(key[2])).only_enforce_if(in_slot)
            complement = sorted({s for s, _ in options[a]} - values)
            if complement:
                model.add_linear_expression_in_domain(slots[a], cp_model.Domain.from_values(complement)).only_enforce_if(in_slot.Not())
            else:
                model.add(in_slot == 1)
            in_room = model.new_bool_var('aula_del_cubell')
            model.add(roomvars[a] == room).only_enforce_if(in_room)
            model.add(roomvars[a] != room).only_enforce_if(in_room.Not())
            model.add(lit <= in_slot)
            model.add(lit <= in_room)
            model.add(lit >= in_slot+in_room-1)
            cache[key] = lit
        return cache[key]

    buckets = defaultdict(list)
    union_cache = {}
    for (date, f, r), uses in usage.items():
        literals = [member(a, r, values) for a, values in uses.items()]
        signature = tuple(sorted(l.index for l in literals))
        if signature not in union_cache:
            used = model.new_bool_var('aula_ocupada')
            model.add_max_equality(used, literals)
            union_cache[signature] = used
        used = union_cache[signature]
        buckets[date, f].append(used)
    seen = set()
    for (date, f), literals in buckets.items():
        available = len(ordinary)-RESERVA_MIN-len(occupied[date, f])
        signature = available, tuple(sorted(l.index for l in literals))
        if signature not in seen:
            model.add(sum(literals) <= available)
            seen.add(signature)
    moves, gaps, room_cost = _objectiu(model, base, acts, slots, roomvars, options, regla)
    # Primer cerquem una assignació d'aula a les franges originals. Si és
    # viable, fixar-les assoleix la cota inferior de zero sessions mogudes.
    original_model = model.clone()
    for a, rows in enumerate(acts):
        for s in rows:
            original_model.add(slots[a] == DIES.index(s.dia)*1440+s.ini)
    first = cp_model.CpSolver()
    first.parameters.max_deterministic_time = min(10, temps_s*.2)
    first.parameters.num_search_workers = 1
    first.parameters.random_seed = llavor
    first.parameters.stop_after_first_solution = True
    initial_status = first.solve(original_model)
    original_ok = initial_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    stats['franja_original_viable'] = original_ok
    stats['estat_franja_original'] = first.status_name(initial_status)
    if original_ok:
        model = original_model
        for v in slots + roomvars:
            model.add_hint(v, first.value(v))
    solver = cp_model.CpSolver()
    solver.parameters.max_deterministic_time = max(.001, temps_s-first.response_proto.deterministic_time)
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = llavor
    stats['temps_construccio_s'] = time.monotonic()-begin
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE) and original_ok:
        solver, status = first, initial_status
    stats.update(estat=solver.status_name(status), temps_s=time.monotonic()-begin,
                 branques=solver.num_branches, conflictes_solver=solver.num_conflicts,
                 treballadors=1, limit_determinista=temps_s,
                 temps_determinista=first.response_proto.deterministic_time + (
                     solver.response_proto.deterministic_time if solver is not first else 0))
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, stats
    stats.update(sessions_noves_fora_franja=sum(solver.value(v) for v in moves),
                 objectiu_hores_mortes_min=sum(solver.value(v) for v in gaps),
                 objectiu_aules=sum(solver.value(v) for v in room_cost),
                 objectiu=solver.objective_value, cota_objectiu=solver.best_objective_bound)
    for a, rows in enumerate(acts):
        slot, r = solver.value(slots[a]), solver.value(roomvars[a])
        for s in rows:
            ref.files[s.id].dia = DIES[slot//1440]
            ref.files[s.id].h_ini = fmt(slot%1440)
            ref.files[s.id].aula = rooms[r]
    return ref, stats


def comprova_proposta(base, proposta, referencia):
    """Comprovació addicional de persones, vincles, torn i rutina del grau nou."""
    col = _col_loca(base, proposta.a_files(), InformeIntern())
    regla = ReglaAlumnat(base.sessions.values())
    today = {s: c for s, c in colloca_avui(base).items() if s in referencia.files}
    inherited = conflictes(today, regla)
    new_conflicts = set(conflictes(col, regla))-set(inherited)
    new_teachers = set(conflictes_docents(col))-set(conflictes_docents(today))
    pairs, _ = parelles_dobles(base)
    doubles = comprova_dobles(base, col, pairs)
    noves = set(base.sessions)-set(referencia.files)
    routine_errors = sum(len({(col[s.id].data.weekday(), col[s.id].ini, col[s.id].aula) for s in rows}) != 1
                         for rows in _activitats(base, noves))
    shift_changes = sum((col[sid].ini < MATI[1]) != (_referencia(base.sessions[sid], referencia)[1] < MATI[1])
                        for sid in referencia.files)
    return {'conflictes_persones_nous': len(new_conflicts | new_teachers),
            'conflictes_alumnat_nous': len(new_conflicts),
            'conflictes_docents_nous': len(new_teachers),
            'dobles_separades': len(doubles['separades']),
            'dobles_amb_aula_propia': sum(bool(col[s.id].aula) for s in base.sessions.values() if s.sense_espai),
            'canvis_torn_52': shift_changes, 'activitats_noves_sense_rutina': routine_errors}


def relaxacions_necessaries(official, proposal, relaxations):
    """Reté només declaracions heretades per a violacions que realment compten.

    Avalua sense relaxar: els conflictes heretats que el jurat ja eximeix
    (inclosos els dobles) no necessiten cap declaració nostra.
    """
    needed = defaultdict(set)
    for v in avalua(official, proposal.a_files()).violacions:
        if v.compta:
            needed[v.regla].update(v.sessions)
    rows = []
    for r in relaxations:
        ids = needed[r.restriccio] & (set(r.sessions) if r.sessions else set(official.sessions))
        if ids:
            rows.append({'restriccio': r.restriccio, 'sessions': '|'.join(sorted(ids)),
                         'justificacio': re.sub(r'(?<![\w/])diagnostic\.md',
                                               '../5.2/diagnostic.md', r.justificacio)})
    return rows


def hores_mortes_grau_nou(official, proposal, referencia):
    """Avalua només les sessions afegides, amb les agendes oficials."""
    base = copy.copy(official)
    base.sessions = {sid: s for sid, s in official.sessions.items() if sid not in referencia.files}
    base.ordre = [sid for sid in official.ordre if sid in base.sessions]
    files = [f for f in proposal.a_files() if f.id in base.sessions]
    return avalua(base, files).objectius['hores_mortes_min']


def publica(stage, out):
    """Substitueix el directori complet, amb rollback si falla el segon rename."""
    backup = stage.parent/'anterior'
    exists = out.exists()
    if exists:
        out.rename(backup)
    try:
        stage.rename(out)
    except BaseException:
        if exists:
            backup.rename(out)
        raise
    if exists:
        shutil.rmtree(backup)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temps', type=float, default=300,
                        help='pressupost de cerca en unitats de temps determinista (no segons de rellotge)')
    parser.add_argument('--llavor', type=int, default=0)
    parser.add_argument('--referencia', type=Path, default=RESULTATS/'5.2'/'proposta.csv')
    args = parser.parse_args(argv)
    out = RESULTATS/'5.4'
    path52 = args.referencia.resolve()
    relax52 = path52.with_name('relaxacions.csv')
    ref = Proposta.llegeix(path52)
    base = carrega_model(GRAU_NOU)
    official = carrega_oficial(GRAU_NOU)
    official52 = carrega_oficial()
    if set(ref.files) != set(official52.sessions):
        raise ValueError('La referència no conté exactament el 5.2 complet')
    relaxations = llegeix_relaxacions(relax52 if relax52.exists() else None)
    proposal, stats = resol_congelat(base, ref, temps_s=args.temps, llavor=args.llavor)
    if proposal is None:
        print('Resposta:', 2 if stats['estat'] == 'INFEASIBLE' else 3, '; solver:', stats['estat'])
        print('No hi ha proposta nova; lliurament anterior conservat íntegrament.')
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.s54-', dir=out.parent) as tmp:
        stage = Path(tmp)/'5.4'
        stage.mkdir()
        # El comptatge compartit espera 5.4 i 5.2 sota una mateixa arrel.
        # L'àlies només serveix per llegir la referència durant la preparació.
        (Path(tmp)/'5.2').mkdir()
        (Path(tmp)/'5.2'/'proposta.csv').symlink_to(path52)
        relax_path = stage/'relaxacions.csv'
        rows = relaxacions_necessaries(official, proposal, relaxations)
        escriu_csv(relax_path, rows, ['restriccio', 'sessions', 'justificacio'])
        relaxations = llegeix_relaxacions(relax_path)
        checks = comprova_proposta(base, proposal, ref)
        report = avalua(official, proposal.a_files(), relaxacions=relaxations)
        if report.veredicte not in VALIDES or any(checks.values()):
            raise ValueError('La proposta candidata no supera les comprovacions')
        path = proposal.escriu(stage/'proposta.csv')
        report = verifica(path, escenari=GRAU_NOU, referencia=path52,
                          relaxacions=relax_path,
                          json_path=stage/'informe.json', violacions_path=stage/'violacions.csv')
        if report.veredicte not in VALIDES or report.compten():
            raise ValueError('El verificador oficial rebutja la proposta; anterior conservada')
        summary = dict(resposta=1, sessions_grau_nou=stats['sessions_noves'],
                       sessions_grau_nou_collocades=stats['sessions_noves'],
                       sessions_grau_nou_fora_franja=stats['sessions_noves_fora_franja'],
                       estat_solver=stats['estat'],
                       relaxacions_per_motiu=dict(Counter({r.justificacio: sum(len(t.sessions) for t in relaxations if t.justificacio == r.justificacio) for r in relaxations})),
                       veredicte=report.veredicte, incompliments_no_declarats=sum(report.compten().values()),
                       **checks)
        summary['canvis_franja_52'] = sum(_referencia(base.sessions[s], ref) != _referencia(base.sessions[s], proposal) for s in ref.files)
        summary['canvis_aula'] = sum(ref.files[s].aula != proposal.files[s].aula for s in ref.files)
        summary['sessions_52_mogudes'] = sum(ref.files[s] != proposal.files[s] for s in ref.files)
        summary['minim_sessions_52_mogudes_demostrat'] = summary['sessions_52_mogudes'] == 0
        summary['minim_sessions_noves_fora_franja_demostrat_amb_regla_equip'] = stats['estat'] == 'OPTIMAL'
        # El costat «abans» és exactament el 5.2, sense sessions extra buides.
        before = avalua(official52, ref.a_files(), relaxacions=relaxations)
        summary['hores_mortes_52_min'] = before.objectius['hores_mortes_min']
        summary['hores_mortes_min'] = report.objectius['hores_mortes_min']
        summary['hores_mortes_grau_nou_min'] = hores_mortes_grau_nou(official, proposal, ref)
        if summary['hores_mortes_grau_nou_min'] != stats['objectiu_hores_mortes_min']:
            raise ValueError('Les hores mortes del grau nou no coincideixen amb l’objectiu')
        escriu_csv(stage/'xifres.csv', [{'xifra': k, 'abans': before.objectius.get(k, 0), 'despres': v}
                                      for k, v in report.objectius.items()] + [
                    {'xifra': 'sessions_grau_nou_fora_franja', 'abans': 0,
                     'despres': summary['sessions_grau_nou_fora_franja']},
                    {'xifra': 'sessions_52_mogudes', 'abans': 0, 'despres': summary['sessions_52_mogudes']}],
                   ['xifra', 'abans', 'despres'])
        for name, obj in [('resum.json', summary), ('execucio.json', stats)]:
            (stage/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        command = f'{PYTHON} -m nivell2.s54 --temps {args.temps:g} --llavor {args.llavor} --referencia {path52}'
        anterior_readme = out/'README.md'
        anterior_text = anterior_readme.read_text(encoding='utf-8') if anterior_readme.exists() else ''
        (stage/'README.md').write_text(conserva_seccions(
        '# 5.4 Grau nou\n\n'
        f"Resposta **{summary['resposta']}**. Estat del solver: {stats['estat']}.\n\n"
        'Model conjunt de dia, hora i aula per activitat, rutina setmanal, mateix torn i sense desdoblaments. '
        'El 5.2 queda congelat; només es conserven les seves relaxacions necessàries. '
        'Objectiu lexicogràfic: franges originals de les sessions noves, hores mortes i aula base/canvis d’aula. '
        'Cerca reproduïble amb un treballador i pressupost de temps determinista (`--temps`), sense límit de rellotge. '
        'La regla addicional d’alumnat és a `nivell2/alumnat.py`: teoria de cohort completa i subgrups prudents. '
        'Només admet PAUL simultanis quan són germans per prefix complet del TE, sufix de la mateixa longitud '
        'i suma d’aforaments compatible. Els altres subgrups es separen perquè les dades no proven que siguin disjunts. '
        f"Sessions noves fora de franja original: {summary['sessions_grau_nou_fora_franja']}; "
        f"classes del 5.2 mogudes: {summary['sessions_52_mogudes']}. "
        'INFEASIBLE en aquestes condicions és resposta 2, no una prova d’impossibilitat global. '
        'UNKNOWN és resposta 3. El detall dels dominis i rebuigs és a `execucio.json`.\n\n'
        + NOTA_GRAU_NOU + '\n\n'
        f'Des del worktree `{ARREL}`:\n```sh\n{command}\n```\n\n'
        'Comprovació oficial de la proposta (si hi ha solució):\n```sh\n'
        f'{PYTHON} -c "from pathlib import Path; from nivell2.base import verifica, GRAU_NOU; '
        f"r=verifica(Path('resultats/nivell2/5.4/proposta.csv'), escenari=GRAU_NOU, "
        f"referencia=Path('{path52}'), relaxacions=Path('resultats/nivell2/5.4/relaxacions.csv')); print(r.veredicte, sum(r.compten().values()))\"\n"
        '```\n\nProves i comprovació de persones:\n```sh\n'
        f'{PYTHON} -m pytest -q nivell2 app\n'
        f'RESULTATS_DIR=$PWD/resultats/nivell2 {PYTHON} -m nivell2.comprova_persones\n```\n', anterior_text), encoding='utf-8')
        readme = stage/'README.md'
        readme.write_text(explica_comptatge(readme.read_text(encoding='utf-8'),
                                           comptatge_verificador('5.4', Path(tmp)), '5.4'),
                          encoding='utf-8')
        publica(stage, out)
    print('Resposta:', summary['resposta'], '; solver:', stats['estat'])
    print('Activitats noves:', stats['activitats_noves'], '; opcions:', sum(stats['opcions_per_activitat']))
    print('Temps de construcció:', round(stats.get('temps_construccio_s', stats['temps_s']), 3),
          '; temps total:', round(stats['temps_s'], 3))
    for key in ('sessions_grau_nou_collocades', 'sessions_grau_nou_fora_franja', 'sessions_52_mogudes',
                'canvis_aula', 'hores_mortes_52_min', 'hores_mortes_grau_nou_min', 'hores_mortes_min',
                'conflictes_persones_nous', 'conflictes_docents_nous', 'incompliments_no_declarats'):
        print(key, ':', summary[key])
    if 'veredicte' in summary:
        print(summary['veredicte'])
    print('Relaxacions heretades:', sum(len(r.sessions) for r in relaxations))
    return 0 if summary['resposta'] in (1, 2) else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('Errors d’execució: 1; lliurament anterior conservat íntegrament')
        raise SystemExit(2)

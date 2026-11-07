"""Reparació local sobre una proposta congelada, sense imprimir dades.

Ús: ``repara(proposta, Canvi(base=base_nova, abans=base_anterior))``.
Les bases són les del model; la proposta d'entrada no es modifica. El resultat
conté la proposta completa (o None), l'estat i recomptes. Només declara el canvi
d'aula imprescindible d'una fixada amb aula tancada. UNKNOWN no prova impossibilitat.
"""
from __future__ import annotations

import copy
import datetime as dt
import time
from collections import defaultdict
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from nivell2.base import Base, Proposta, fmt
from nivell2.franges import _referencia, _regles
from nivell2.comprova_persones import parelles_dobles
from horaris.check import _espai_ok, passadis, FRANGES, RESERVA_MIN
from horaris.model import DIES, MATI, TARDA

MOTIU_AULA_FIXADA = ('L’aula de la sessió fixada està tancada per una contingència; '
                     'és imprescindible canviar només l’aula, conservant el dia, l’hora i el torn.')


@dataclass
class Canvi:
    base: Base
    abans: Base
    temps_s: float = 40
    llavor: int = 0


@dataclass
class Reparacio:
    proposta: Proposta | None
    estat: str
    estadistiques: dict = field(default_factory=dict)
    relaxacions: list[dict] = field(default_factory=list)


def afectades(proposta, canvi):
    """Imprevistos mesurats sobre el 5.2, inclòs el grup que creix tot el curs."""
    base = canvi.base
    out = {'aula_reservada': set(), 'aula_avariada': set(),
           'grup_creix': set(), 'recuperacio': set(base.cancellades)}
    for sid, s in base.sessions.items():
        data, ini = _referencia(s, proposta)
        if s.alumnes > canvi.abans.sessions[sid].alumnes:
            out['grup_creix'].add(sid)
        for t in base.tancaments:
            if (not s.sense_espai and proposta.files[sid].aula == t.aula
                    and t.data_ini <= data <= t.data_fi and ini < t.fi and ini+s.durada > t.ini):
                key = 'aula_reservada' if t.data_ini != t.data_fi else 'aula_avariada'
                out[key].add(sid)
    return out


def _unitats(base):
    units = defaultdict(list)
    for s in base.sessions.values():
        units[s.unitat].append(s)
    parent = {u: u for u in units}

    def root(u):
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    pairs, _ = parelles_dobles(base)
    for sid, hosts in pairs.items():
        for host in hosts:
            parent[root(base.sessions[host].unitat)] = root(base.sessions[sid].unitat)
    return dict(units), {u: root(u) for u in units}


def _solapa(a, da, b, db):
    return da[0] == db[0] and da[1] < db[1]+b.durada and db[1] < da[1]+a.durada


def _fixada_tancada(base, s, ref):
    date, ini = _referencia(s, ref)
    return bool(s.fixada or s.tipus == 'PLAB') and any(t.aula == ref.files[s.id].aula
        and t.data_ini <= date <= t.data_fi and ini < t.fi and ini+s.durada > t.ini
        for t in base.tancaments)


def _heretats(base, ref):
    """Parells crus del 5.2: no reutilitza conflictes de la partida ni deduplica compartides."""
    days = defaultdict(list)
    for s in base.sessions.values():
        date, ini = _referencia(s, ref)
        days[date].append((ini, s.id, s))
    out = set()
    for rows in days.values():
        rows.sort(key=lambda row: row[:2])
        for i, (ini, _, a) in enumerate(rows):
            for start, _, b in rows[i+1:]:
                if start >= ini+a.durada:
                    break
                pair = tuple(sorted((a.id, b.id)))
                out.update((rule, pair) for rule in _regles(a, b))
    return out


def _franges(base, rows, ref, amplia, recuperades=()):
    """Només la recuperació canvia de dia; la resta, com a màxim d'hora."""
    original = {_referencia(s, ref) for s in rows}
    if len(original) != 1:
        return []
    date, start = next(iter(original))
    cancelled = [s for s in [*rows, *recuperades] if s.id in base.cancellades]
    if cancelled:
        first = max(s.data for s in cancelled)+dt.timedelta(days=1)
        last = min(base.cancellades[s.id] for s in cancelled)
        dates = [first+dt.timedelta(days=d) for d in range(max(0, (last-first).days+1))]
    else:
        dates = [date]
    lo, hi = MATI if start < MATI[1] else TARDA
    duration = max(s.durada for s in rows)
    starts = sorted({start, *range(lo, hi-duration+1, 30)}) if cancelled or amplia else [start]
    out = []
    for d in dates:
        if d.weekday() >= 5 or (d != date and d in base.dies_sense_classe):
            continue
        # Les files no cancel·lades no poden expressar una altra setmana.
        if any(s.id not in base.cancellades and d.isocalendar()[:2] != s.data.isocalendar()[:2] for s in rows):
            continue
        for ini in starts:
            if not lo <= ini <= hi-duration:
                continue
            if any((s.fixada or s.tipus == 'PLAB') and s.id not in base.cancellades
                   and (d, ini) != _referencia(s, ref) for s in rows):
                continue
            if any(ini < b and ini+duration > a for a, b in base.aturades.get(d, ())):
                # Mateixa excepció d'avaluació que el verificador oficial.
                if not all(d == s.data and any(s.ini < b and s.fi > a
                           for a, b in base.aturades.get(d, ())) for s in rows):
                    continue
            out.append((d, ini))
    return out


def _resol(base, units, links, opened, ref, inherited, deadline, seed, amplia, pressupost):
    begin = time.monotonic()
    _resol.diagnostic = {}
    model = cp_model.CpModel()
    current = {sid: _referencia(s, ref) for sid, s in base.sessions.items()}
    fixed = defaultdict(list)
    for u, rows in units.items():
        if u not in opened:
            for s in rows:
                fixed[current[s.id][0]].append(s)
    rooms = sorted(set(base.aules) | {a.aula for a in ref.files.values()} | {''})
    rid = {r: i for i, r in enumerate(rooms)}
    starts, roomvars, intervals, options = {}, {}, {}, {}
    reserve = defaultdict(list)
    ordinaries = {r for r, a in base.aules.items() if a.ordinaria}
    fixed_occupied = defaultdict(set)
    for date, rows in fixed.items():
        for s in rows:
            room = ref.files[s.id].aula
            if room in ordinaries and not s.sense_espai:
                _, ini = current[s.id]
                for f in FRANGES:
                    if ini < f+60 and ini+s.durada > f:
                        fixed_occupied[date, f].add(room)

    def blocked(a, b):
        if a.unitat == b.unitat or links[a.unitat] == links[b.unitat]:
            return False
        pair = tuple(sorted((a.id, b.id)))
        return any((rule, pair) not in inherited or a.id in base.cancellades
                   or b.id in base.cancellades for rule in _regles(a, b))

    costs_time, costs_room, costs_corridor = [], [], []
    acts = defaultdict(list)
    for u in sorted(opened):
        if time.monotonic() >= deadline:
            return None, 'UNKNOWN'
        rows = units[u]
        physical = [s for s in rows if not s.sense_espai]
        duration = max(s.durada for s in rows)
        allowed = (set(base.aules) | {s.aula for s in physical if s.aula == 'B3/0021'}) if physical else {''}
        for s in physical:
            compatible_rooms = {r for r in base.aules if _espai_ok(base, s, r)}
            if s.aula == 'B3/0021':
                compatible_rooms.add(s.aula)
            allowed &= compatible_rooms
            if ((s.tipus == 'PLAB' or (s.fixada and s.aula))
                    and s.id not in base.cancellades and not _fixada_tancada(base, s, ref)):
                allowed &= {ref.files[s.id].aula}
            # No es porta cap classe nova a una aula externa.
            if s.aula == 'B3/0021':
                allowed &= {ref.files[s.id].aula}
        n = sum(s.alumnes for s in physical)
        compatible = len(allowed)
        allowed = {r for r in allowed if r not in base.aules or base.aules[r].capacitat >= n}
        candidates = []
        recovered = [s for v in opened if links[v] == links[u] for s in units[v]
                     if s.id in base.cancellades]
        slots = _franges(base, rows, ref, amplia, recovered)
        blocked_people = blocked_room = blocked_closure = 0
        for date, ini in slots:
            obstacles = fixed[date]
            if any(_solapa(s, (date, ini), t, current[t.id]) and blocked(s, t)
                   for s in rows for t in obstacles):
                blocked_people += 1
                continue
            for room in sorted(allowed):
                if any(t.aula == room and t.data_ini <= date <= t.data_fi
                       and ini < t.fi and ini+duration > t.ini for t in base.tancaments):
                    blocked_closure += 1
                    continue
                if room and any(not t.sense_espai and ref.files[t.id].aula == room
                                and _solapa(s, (date, ini), t, current[t.id])
                                for s in physical for t in obstacles):
                    blocked_room += 1
                    continue
                candidates.append((date.toordinal()*1440+ini, rid[room]))
        if not candidates:
            _resol.diagnostic = {'domini_buit': 1, 'membres': len(rows), 'alumnes': n,
                'aules_compatibles': compatible, 'aules_amb_aforament': len(allowed),
                'franges': len(slots), 'franges_bloquejades_persones': blocked_people,
                'opcions_bloquejades_aula': blocked_room, 'opcions_bloquejades_tancament': blocked_closure,
                'fixades': sum(bool(s.fixada) for s in rows),
                'plab': sum(s.tipus == 'PLAB' for s in rows),
                'dobles': sum(s.sense_espai for s in rows)}
            return None, 'INFEASIBLE'
        options[u] = candidates
        x = starts[u] = model.new_int_var_from_domain(cp_model.Domain.from_values(sorted({t for t, _ in candidates})), 'franja')
        r = roomvars[u] = model.new_int_var_from_domain(cp_model.Domain.from_values(sorted({r for _, r in candidates})), 'aula')
        model.add_allowed_assignments([x, r], candidates)
        intervals[u] = model.new_fixed_size_interval_var(x, duration, 'classe')
        for s in rows:
            date, ini = current[s.id]
            diff = model.new_bool_var('canvi_franja')
            model.add(x != date.toordinal()*1440+ini).only_enforce_if(diff)
            model.add(x == date.toordinal()*1440+ini).only_enforce_if(diff.Not())
            costs_time.append(diff)
            diff = model.new_bool_var('canvi_aula')
            model.add(r != rid[ref.files[s.id].aula]).only_enforce_if(diff)
            model.add(r == rid[ref.files[s.id].aula]).only_enforce_if(diff.Not())
            # El verificador no compta el canvi d'aula de les recuperades.
            if s.id not in base.cancellades:
                costs_room.append(diff)
            if not s.sense_espai:
                acts[s.activitat or s.id].append(u)
        # Cada opció activa exactament una aula i els cubells R8 corresponents.
        for room in sorted({room for _, room in candidates}):
            if not rooms[room]:
                continue
            use = model.new_bool_var('usa_aula')
            model.add(r == room).only_enforce_if(use)
            model.add(r != room).only_enforce_if(use.Not())
            optional = model.new_optional_fixed_size_interval_var(x, duration, use, 'ocupacio')
            reserve['interval', room].append(optional)
        for stamp, room in candidates:
            date = dt.date.fromordinal(stamp//1440)
            ini = stamp % 1440
            if rooms[room] in ordinaries:
                for f in FRANGES:
                    if ini < f+60 and ini+duration > f:
                        reserve['bucket', date, f, rooms[room]].append((u, stamp, room))
        for s in physical:
            penalty = model.new_bool_var('fora_passadis')
            model.add_allowed_assignments([r, penalty], [(v, int(passadis(rooms[v]) != passadis(ref.files[s.id].aula)))
                for v in sorted({v for _, v in candidates})])
            costs_corridor.append(penalty)

    us = sorted(opened)
    for i, u in enumerate(us):
        if time.monotonic() >= deadline:
            return None, 'UNKNOWN'
        for v in us[i+1:]:
            if links[u] == links[v]:
                model.add(starts[u] == starts[v])
            elif any(blocked(a, b) for a in units[u] for b in units[v]):
                model.add_no_overlap([intervals[u], intervals[v]])
    for key, xs in list(reserve.items()):
        if key[0] == 'interval':
            model.add_no_overlap(xs)
    # R8 compta aules diferents, també per dues classes successives en una hora.
    bucket_uses = defaultdict(list)
    for key, entries in list(reserve.items()):
        if time.monotonic() >= deadline:
            return None, 'UNKNOWN'
        if key[0] != 'bucket':
            continue
        _, date, f, room = key
        if room in fixed_occupied[date, f]:
            continue
        active = []
        by_unit = defaultdict(set)
        for u, stamp, r in entries:
            by_unit[u].add((stamp, r))
        for u, pairs in by_unit.items():
            b = model.new_bool_var('ocupa_cubell')
            model.add_allowed_assignments([starts[u], roomvars[u], b],
                [(stamp, r, int((stamp, r) in pairs)) for stamp, r in options[u]])
            active.append(b)
        used = model.new_bool_var('aula_ocupada')
        model.add_max_equality(used, active)
        bucket_uses[date, f].append(used)
    if len(ordinaries) >= RESERVA_MIN:
        for key, xs in bucket_uses.items():
            model.add(sum(xs)+len(fixed_occupied[key]) <= len(ordinaries)-RESERVA_MIN)
    # La rutina inclou les setmanes congelades de les activitats obertes.
    for u, rows in units.items():
        if u not in opened:
            for s in rows:
                if not s.sense_espai and (s.activitat or s.id) in acts:
                    acts[s.activitat or s.id].append(u)
    routine = []
    for members in acts.values():
        members = sorted(set(members), key=lambda u: (current[units[u][0].id], u))
        for u, v in zip(members, members[1:]):
            if u not in opened and v not in opened:
                continue
            diff = model.new_bool_var('excepcio_rutina')
            a = roomvars[u] if u in opened else rid[ref.files[units[u][0].id].aula]
            b = roomvars[v] if v in opened else rid[ref.files[units[v][0].id].aula]
            model.add(a != b).only_enforce_if(diff)
            model.add(a == b).only_enforce_if(diff.Not())
            routine.append(diff)
    gaps = _hores_mortes(model, base, units, starts, options, current, opened)
    # Lexicogràfic: canvis oficials, passadís, hores mortes i rutina.
    quality = sum(routine)
    weight = len(routine)+1
    quality += weight*sum(gaps)
    weight *= 1440*len(gaps)+1
    quality += weight*sum(costs_corridor)
    weight *= len(costs_corridor)+1
    quality += weight*sum(costs_room)
    weight *= len(costs_room)+1
    model.minimize(weight*sum(costs_time)+quality)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(.001, deadline-time.monotonic())
    solver.parameters.num_search_workers = 1
    # Límit de feina reproduïble, amb el rellotge només com a salvaguarda.
    solver.parameters.max_deterministic_time = max(.01, pressupost/2)
    solver.parameters.random_seed = seed
    _resol.diagnostic = {'construccio_ms': round(1000*(time.monotonic()-begin)),
                        'variables': len(model.proto.variables),
                        'restriccions': len(model.proto.constraints)}
    # solve optimitza fins a OPTIMAL o fins a consumir el pressupost; no hi ha
    # cap callback que aturi la cerca en trobar el primer FEASIBLE.
    status = solver.solve(model)
    state = solver.status_name(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, state
    proposal = copy.deepcopy(ref)
    for u in opened:
        stamp, room = solver.value(starts[u]), rooms[solver.value(roomvars[u])]
        date, ini = dt.date.fromordinal(stamp//1440), stamp % 1440
        for s in units[u]:
            a = proposal.files[s.id]
            a.dia, a.h_ini, a.aula = DIES[date.weekday()], fmt(ini), '' if s.sense_espai else room
            a.data = date.isoformat() if s.id in base.cancellades else ''
    return proposal, state


def _hores_mortes(m, base, units, starts, options, current, opened):
    """Minuts entre sessions consecutives, amb els subgrups del verificador.

    L'ordre és per inici i id, també quan hi ha solapaments heretats.
    No compta el migdia ni replica una teoria per subgrups absents aquell dia.
    """
    # Només les dates possibles i les agendes que poden canviar. Inclou totes
    # les classes congelades d'aquells dies i la recuperació entre setmanes.
    moving = {u for u, values in options.items() if len({stamp for stamp, _ in values}) > 1}
    if not moving:
        return []
    dates = {stamp//1440 for u in moving for stamp, _ in options[u]}
    origin = min(dates)*1440
    horizon = max(dates)-min(dates)+2
    sentinel = horizon*1440
    relevant = {u: rows for u, rows in units.items()
                if u in moving or current[rows[0].id][0].toordinal() in dates}
    starts = {u: starts[u]-origin if u in opened else
              current[rows[0].id][0].toordinal()*1440+current[rows[0].id][1]-origin
              for u, rows in relevant.items()}
    units = relevant
    weeks = {0: sorted(units)}
    costs = []
    days, minutes = {}, {}
    for u, x in starts.items():
        days[u] = m.new_int_var(0, horizon, 'dia_agenda')
        minutes[u] = m.new_int_var(0, 1439, 'minut_agenda')
        m.add_division_equality(days[u], x, 1440)
        m.add_modulo_equality(minutes[u], x, 1440)
    same_days, later_starts = {}, {}

    def same_day(u, v):
        key = tuple(sorted((u, v)))
        if key not in same_days:
            eq = m.new_bool_var('mateix_dia')
            m.add(days[u] == days[v]).only_enforce_if(eq)
            m.add(days[u] != days[v]).only_enforce_if(eq.Not())
            same_days[key] = eq
        return same_days[key]

    def later_start(u, v):
        key = (u, v)
        if key not in later_starts:
            later = m.new_bool_var('posterior')
            tie = min(s.id for s in units[u]) < min(s.id for s in units[v])
            m.add(starts[v] >= starts[u] + (0 if tie else 1)).only_enforce_if(later)
            m.add(starts[v] < starts[u] + (0 if tie else 1)).only_enforce_if(later.Not())
            value = m.new_int_var(0, sentinel, 'candidat_seguent')
            m.add(value == starts[v]).only_enforce_if(later)
            m.add(value == sentinel).only_enforce_if(later.Not())
            later_starts[key] = value
        return later_starts[key]

    for week, us in weeks.items():
        theory, groups = defaultdict(set), defaultdict(set)
        for u in us:
            for row in units[u]:
                for coh in row.cohorts:
                    key = (coh, row.linia)
                    if row.tipus == 'TE':
                        theory[key].add(u)
                    else:
                        groups[key + (row.num_grup,)].add(u)
        # '*' handles days with theory but no actual subgroup present.
        for key in theory:
            groups[key + ('*',)] = set()
        for key, practice in groups.items():
            members = practice | theory[key[:2]]
            if len(members) < 2 or not members & moving:
                continue
            all_practice = set().union(*(v for k, v in groups.items() if k[:2] == key[:2]))
            for u in sorted(members):
                following = m.new_int_var(0, sentinel, 'seguent')
                m.add_min_equality(following, [later_start(u, v) for v in sorted(members) if v != u])
                nextday = m.new_int_var(0, horizon, 'dia_seguent')
                nextminute = m.new_int_var(0, 1439, 'minut_seguent')
                m.add_division_equality(nextday, following, 1440)
                m.add_modulo_equality(nextminute, following, 1440)
                same = m.new_bool_var('seguent_mateix_dia')
                m.add(nextday == days[u]).only_enforce_if(same)
                m.add(nextday != days[u]).only_enforce_if(same.Not())
                am = m.new_bool_var('final_mati')
                bm = m.new_bool_var('seguent_mati')
                duration = max(row.durada for row in units[u])
                m.add(minutes[u] + duration <= MATI[1]).only_enforce_if(am)
                m.add(minutes[u] + duration > MATI[1]).only_enforce_if(am.Not())
                m.add(nextminute < MATI[1]).only_enforce_if(bm)
                m.add(nextminute >= MATI[1]).only_enforce_if(bm.Not())
                shift = m.new_bool_var('mateix_torn')
                m.add(am == bm).only_enforce_if(shift)
                m.add(am != bm).only_enforce_if(shift.Not())
                active = m.new_bool_var('subgrup_present')
                if u in practice:
                    m.add(active == 1)
                else:
                    present = [same_day(u, v) for v in sorted(all_practice if key[2] == '*' else practice)]
                    if present:
                        any_present = m.new_bool_var('practiques_aquell_dia')
                        m.add_max_equality(any_present, present)
                        m.add(active == (1 - any_present if key[2] == '*' else any_present))
                    else:
                        m.add(active == (1 if key[2] == '*' else 0))
                count = m.new_bool_var('compta_buit')
                m.add_bool_and([same, shift, active]).only_enforce_if(count)
                m.add_bool_or([same.Not(), shift.Not(), active.Not()]).only_enforce_if(count.Not())
                gap = m.new_int_var(0, sentinel, 'buit_positiu')
                m.add_max_equality(gap, [0, following-starts[u]-duration])
                cost = m.new_int_var(0, 1440, 'minuts_morts')
                m.add(cost == gap).only_enforce_if(count)
                m.add(cost == 0).only_enforce_if(count.Not())
                costs.append(cost)
    return costs


def repara(proposta: Proposta, canvi: Canvi) -> Reparacio:
    """Fixa la referència i obre afectades, veïnes, dia i setmana, per aquest ordre.

    Mai canvia de torn. INFEASIBLE es refereix només al veïnat provat, no al
    problema global. El pressupost inclou la construcció de tots els intents.
    """
    start = time.monotonic()
    if canvi.temps_s <= 0 or set(proposta.files) != set(canvi.base.sessions) or set(canvi.abans.sessions) != set(canvi.base.sessions):
        raise ValueError('Pressupost invàlid o proposta i bases incompatibles')
    base = canvi.base
    reasons = afectades(proposta, canvi)
    affected = set().union(*reasons.values())
    stats = {'sessions_afectades_per_imprevist': {k: len(v) for k, v in reasons.items()},
             'sessions_afectades': len(affected), 'intents': [], 'sessions_obertes': 0,
             'canvis_franja_vs_referencia': 0, 'canvis_aula_vs_referencia': 0}
    if not affected:
        return Reparacio(copy.deepcopy(proposta), 'OPTIMAL', {**stats, 'temps_s': time.monotonic()-start})
    units, links = _unitats(base)
    inherited = _heretats(base, proposta)
    opened = {base.sessions[sid].unitat for sid in affected}
    reference = {sid: _referencia(s, proposta) for sid, s in base.sessions.items()}
    for level in range(5):
        components = {links[u] for u in opened}
        opened |= {u for u in units if links[u] in components}
        proposal, state = _resol(base, units, links, opened, proposta, inherited,
            start+canvi.temps_s, canvi.llavor, amplia=level >= 2, pressupost=canvi.temps_s)
        stats['intents'].append({'nivell': level, 'estat': state,
                               'sessions_obertes': sum(len(units[u]) for u in opened),
                               'diagnostic': dict(_resol.diagnostic)})
        if proposal is not None:
            stats.update(temps_s=time.monotonic()-start,
                         sessions_obertes=sum(len(units[u]) for u in opened),
                         canvis_franja_vs_referencia=sum(_referencia(s, proposal) != reference[sid] for sid, s in base.sessions.items()),
                         canvis_aula_vs_referencia=sum(proposal.files[sid].aula != a.aula for sid, a in proposta.files.items()))
            forced = defaultdict(list)
            for sid, s in base.sessions.items():
                if (_fixada_tancada(base, s, proposta) and proposal.files[sid].aula != proposta.files[sid].aula
                        and (s.tipus == 'PLAB' or s.aula) and s.aula != proposal.files[sid].aula):
                    forced['R7-PLAB' if s.tipus == 'PLAB' else 'R1-FIXADA'].append(sid)
            relaxations = [{'restriccio': rule, 'sessions': '|'.join(sorted(ids)),
                            'justificacio': MOTIU_AULA_FIXADA} for rule, ids in sorted(forced.items())]
            return Reparacio(proposal, state, stats, relaxations)
        if state != 'INFEASIBLE' or time.monotonic() >= start+canvi.temps_s:
            break
        rows = [s for u in opened for s in units[u]]
        dates = {reference[s.id][0] for s in rows}
        dates |= {s.data+dt.timedelta(days=d) for s in rows if s.id in base.cancellades
                  for d in range(1, (base.cancellades[s.id]-s.data).days+1)}
        compatible = {t.id: {r for r, a in base.aules.items() if not t.sense_espai
                      and a.capacitat >= t.alumnes and _espai_ok(base, t, r)} for t in rows}

        def neighbour(s, t):
            related = (s.docents & t.docents or set(s.cohorts) & set(t.cohorts)
                       or proposta.files[s.id].aula in compatible[t.id])
            if not related:
                return False
            if _solapa(s, reference[s.id], t, reference[t.id]):
                return True
            return (t.id in base.cancellades and t.data < reference[s.id][0] <= base.cancellades[t.id]
                    and (reference[s.id][1] < MATI[1]) == (reference[t.id][1] < MATI[1]))

        for u, ss in units.items():
            # Les fixades intactes continuen sent obstacles, sense variables.
            if any((s.fixada or s.tipus == 'PLAB') and s.id not in base.cancellades
                   and not _fixada_tancada(base, s, proposta) for s in ss):
                continue
            if any((reference[s.id][0] in dates and (level >= 1 or (
                    any(neighbour(s, t) for t in rows))))
                   or (level >= 2 and any(reference[s.id][0].isocalendar()[:2] == d.isocalendar()[:2] for d in dates))
                   for s in ss):
                opened.add(u)
    stats['temps_s'] = time.monotonic()-start
    return Reparacio(None, state, stats)

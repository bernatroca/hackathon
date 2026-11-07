"""Assignació d'espais amb franges decidides; regles importades del verificador."""
from collections import defaultdict
import time

from ortools.sat.python import cp_model
from nivell2.base import Proposta
from horaris.check import _espai_ok, passadis, FRANGES, RESERVA_MIN
from horaris.model import a_traslladar

PES_CANVI = 3
PES_PASSADIS = 2
PES_AULA_BASE = 1


def assigna_aules(base, franges, *, referencia=None, fixes=frozenset(), temps_s=300, llavor=0):
    """Retorna (id_sessio -> aula, estat CP-SAT).

    franges ha de contenir exactament les sessions: id -> (datetime.date, minut).
    referencia és una Proposta (per defecte la partida); fixes fixa l'aula de
    referència. PLAB i fixades R1 amb aula conserven l'original. Les dobles
    retornen ''. Els defectes d'aforament fixats i inalterats es conserven
    com a heretats, igual que al verificador. UNKNOWN/INFEASIBLE sense solució retornen {}.
    Primer prova aula única per activitat. Si és INFEASIBLE permet excepcions,
    amb cost superior a la suma màxima dels objectius secundaris. temps_s és
    el pressupost del solver compartit entre intents (construcció exclosa).
    """
    if set(franges) != set(base.sessions):
        raise ValueError('franges ha de contenir exactament totes les sessions')
    if not set(fixes) <= set(base.sessions):
        raise ValueError('fixes conté sessions desconegudes')
    if temps_s <= 0:
        raise ValueError('temps_s ha de ser positiu')
    ref = (referencia or Proposta.de_base(base)).files
    if not set(base.sessions) <= set(ref):
        raise ValueError('referencia incompleta')
    units = defaultdict(list)
    result = {}
    for sid, s in base.sessions.items():
        if s.sense_espai:
            result[sid] = ''
        else:
            units[s.unitat].append(s)
    rooms = sorted(set(base.aules) | {s.aula for ss in units.values() for s in ss} | {''})
    rid = {a: i for i, a in enumerate(rooms)}
    domains, times, acts = {}, {}, defaultdict(set)
    for u, ss in units.items():
        slots = {franges[s.id] for s in ss}
        if len(slots) != 1:
            return {}, 'INFEASIBLE'
        date, start = next(iter(slots))
        times[u] = (date, start, max(start + s.durada for s in ss))
        candidates = set(base.aules)
        for s in ss:
            fixed = None
            if s.tipus == 'PLAB' or (s.fixada and s.aula and not a_traslladar(s.aula)):
                fixed = s.aula
            if s.aula == 'B3/0021' and franges[s.id] == (s.data, s.ini):
                fixed = s.aula
            if s.id in fixes:
                if fixed is not None and fixed != ref[s.id].aula:
                    return {}, 'INFEASIBLE'
                fixed = ref[s.id].aula
            allowed = {a for a in base.aules if _espai_ok(base, s, a)}
            # The verifier exempts the unchanged original room from type checks.
            if s.aula in base.aules and not (s.tipus != 'PLAB' and base.aules[s.aula].tipus == 'Laboratoris docents'):
                allowed.add(s.aula)
            if fixed is not None:
                if fixed and fixed not in base.aules and fixed != s.aula:
                    return {}, 'INFEASIBLE'
                allowed = {fixed}
                candidates.add(fixed)
            candidates &= allowed
            acts[s.activitat or s.id].add(u)
        n = sum(s.alumnes for s in ss)
        candidates = {a for a in candidates if (a not in base.aules or base.aules[a].capacitat >= n or all(s.fixada and s.aula == a for s in ss))
                      and not any(t.aula == a and t.data_ini <= date <= t.data_fi
                                  and start < t.fi and times[u][2] > t.ini for t in base.tancaments)}
        if not candidates:
            return {}, 'INFEASIBLE'
        domains[u] = sorted(rid[a] for a in candidates)

    # Student agendas use precisely the verifier's cohort/line/subgroup definition.
    agenda = defaultdict(list)
    for u, ss in units.items():
        for s in ss:
            for coh in s.cohorts:
                agenda[coh, s.linia, times[u][0], '*' if s.tipus == 'TE' else s.num_grup].append(u)
    pairs = defaultdict(int)
    keys = {k[:3] for k in agenda}
    for key in sorted(keys):
        subs = sorted(k[3] for k in agenda if k[:3] == key and k[3] != '*') or ['*']
        for sub in subs:
            us = agenda.get((*key, '*'), []) + (agenda.get((*key, sub), []) if sub != '*' else [])
            us = sorted(set(us), key=lambda u: (times[u][1], units[u][0].id))
            for a, b in zip(us, us[1:]):
                pairs[a, b] += 1
    elapsed = 0
    for strict in (True, False):
        model = cp_model.CpModel()
        parent = {u: u for u in units}
        def root(u):
            while parent[u] != u:
                parent[u] = parent[parent[u]]
                u = parent[u]
            return u
        if strict:
            for us in acts.values():
                us = sorted(us)
                for u in us[1:]:
                    parent[root(u)] = root(us[0])
        grouped = defaultdict(list)
        for u in units:
            grouped[root(u)].append(u)
        shared_vars = {}
        for r, us in grouped.items():
            ds = set(domains[us[0]])
            for u in us[1:]:
                ds.intersection_update(domains[u])
            if not ds:
                model.add(False)
                ds = {0}
            shared_vars[r] = model.new_int_var_from_domain(cp_model.Domain.from_values(sorted(ds)), r)
        var = {u: shared_vars[root(u)] for u in units}
        equal_cache = {}
        def isroom(u, r):
            if r not in domains[u]:
                return 0
            key = (root(u), r)
            if key not in equal_cache:
                v = model.new_bool_var('room')
                model.add(var[u] == r).only_enforce_if(v)
                model.add(var[u] != r).only_enforce_if(v.Not())
                equal_cache[key] = v
            return equal_cache[key]
        secondary, routine = [], []
        for act, us in acts.items():
            us = sorted(us)
            if not strict:
                center = model.new_int_var(0, len(rooms)-1, 'routine')
                for u in us:
                    different = model.new_bool_var('exception')
                    model.add(var[u] == center).only_enforce_if(different.Not())
                    model.add(var[u] != center).only_enforce_if(different)
                    routine.append(different)
        dates = defaultdict(list)
        for u, (d, start, end) in times.items():
            dates[d].append(u)
        ordinary = [rid[a] for a, x in base.aules.items() if x.ordinaria]
        for d, us in dates.items():
            us.sort(key=lambda u: times[u][1])
            for i, a in enumerate(us):
                for b in us[i+1:]:
                    if times[b][1] >= times[a][2]:
                        break
                    if domains[a] != [rid['']] and domains[b] != [rid['']]:
                        model.add(var[a] != var[b])
            if len(ordinary) >= RESERVA_MIN:
                for f in FRANGES:
                    active = [u for u in us if times[u][1] < f+60 and times[u][2] > f]
                    occupied = []
                    for r in ordinary:
                        bs = [isroom(u, r) for u in active if r in domains[u]]
                        if bs:
                            occ = model.new_bool_var('occupied')
                            model.add_max_equality(occ, bs)
                            occupied.append(occ)
                    model.add(sum(occupied) <= len(ordinary)-RESERVA_MIN)
        for u, ss in units.items():
            for s in ss:
                a = ref[s.id].aula
                if a and not a_traslladar(a):
                    secondary.append(PES_CANVI * (1-isroom(u, rid[a])) if a in rid else PES_CANVI)
        corridors = {a: i for i, a in enumerate(sorted({passadis(a) for a in rooms}))}
        corridor_var = {}
        for u in var:
            c = model.new_int_var(0, len(corridors)-1, 'corridor')
            model.add_allowed_assignments([var[u], c], [(r, corridors[passadis(rooms[r])]) for r in domains[u]])
            corridor_var[u] = c
        for (a, b), count in pairs.items():
            if domains[a] == [rid['']] or domains[b] == [rid['']]:
                continue
            diff = model.new_bool_var('walk')
            model.add(corridor_var[a] != corridor_var[b]).only_enforce_if(diff)
            model.add(corridor_var[a] == corridor_var[b]).only_enforce_if(diff.Not())
            secondary.append(PES_PASSADIS * count * diff)
        te = defaultdict(set)
        for u, ss in units.items():
            for s in ss:
                if s.tipus == 'TE':
                    for coh in s.cohorts:
                        te[coh, s.linia].add(u)
        for us in te.values():
            for r in sorted({r for u in us for r in domains[u]}):
                used = model.new_bool_var('base_room')
                model.add_max_equality(used, [isroom(u, r) for u in us])
                secondary.append(PES_AULA_BASE * used)
        bound = PES_CANVI*len(base.sessions) + PES_PASSADIS*sum(pairs.values()) + sum(len(us)*len(rooms) for us in te.values()) + 1
        model.minimize(sum(secondary) + bound*sum(routine))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(.01, temps_s-elapsed)
        solver.parameters.num_search_workers = 2
        solver.parameters.random_seed = llavor
        begin = time.monotonic()
        status = solver.solve(model)
        elapsed += time.monotonic()-begin
        name = solver.status_name(status)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for u, ss in units.items():
                for s in ss:
                    result[s.id] = rooms[solver.value(var[u])]
            return result, name
        if status != cp_model.INFEASIBLE or not strict or elapsed >= temps_s:
            return {}, name
    return {}, 'UNKNOWN'

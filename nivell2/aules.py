"""Assignació d'espais amb franges decidides; regles importades del verificador."""
from collections import defaultdict, Counter
import time

from ortools.sat.python import cp_model
from nivell2.base import Proposta
from horaris.check import _espai_ok, passadis, FRANGES, RESERVA_MIN
from horaris.model import a_traslladar

PES_CANVI = 3
PES_PASSADIS = 2
PES_AULA_BASE = 10000
PES_TE_FORA_BASE = 1000
PES_PAUL_FORA_BASE = 200
PES_MATEIXA_AULA = 1
PES_TRANSICIO_TE_PAUL = 1000


def assigna_aules(base, franges, *, referencia=None, fixes=frozenset(), temps_s=300, llavor=0,
                  pista=None, en_solucio=None, agrupa_te=False, millora_local=False):
    """Retorna (id_sessio -> aula, estat CP-SAT).

    agrupa_te: prova de concentració TE; uneix grups compatibles amb les
    finestres, dominis i fixacions. Si no troba solució aviat, reintenta sense unions.
    millora_local: activa LNS amb pista vàlida; False manté cerca general
    (p. ex. quan el 5.2 ha canviat les franges de la pista).
    pista: Proposta opcional per AddHint, independent de referencia (costos).
    en_solucio: callback opcional (assignacio, estat), a cada incumbent.
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
    attempts = [(True, True), (True, False), (False, False)] if agrupa_te else [(True, False), (False, False)]
    for strict, merge_te in attempts:
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
        if merge_te:
            # Concentrate theory groups when the union has a common domain and
            # no simultaneous physical classes. Conflicts remain hard below.
            student_te = defaultdict(set)
            for u, ss in units.items():
                for s in ss:
                    if s.tipus == 'TE':
                        for coh in s.cohorts:
                            student_te[coh, s.linia].add(u)
            members = defaultdict(set)
            for u in units:
                members[root(u)].add(u)
            for key, us in sorted(student_te.items(), key=lambda kv: (-len(kv[1]), kv[0])):
                roots = {root(u) for u in us}
                all_units = set().union(*(members[r] for r in roots))
                common = set.intersection(*(set(domains[u]) for u in all_units))
                if not common:
                    continue
                bydate = defaultdict(list)
                for u in all_units:
                    bydate[times[u][0]].append(u)
                collision = False
                for xs in bydate.values():
                    xs.sort(key=lambda u: times[u][1])
                    if any(times[a][2] > times[b][1] for a, b in zip(xs, xs[1:])):
                        collision = True
                        break
                if collision:
                    continue
                target = min(roots)
                for r in roots:
                    parent[r] = target
                members[target] = all_units
        grouped = defaultdict(list)
        for u in units:
            grouped[root(u)].append(u)
        shared_vars = {}
        group_domains = {}
        for r, us in grouped.items():
            ds = set(domains[us[0]])
            for u in us[1:]:
                ds.intersection_update(domains[u])
            if not ds:
                model.add(False)
                ds = {0}
            group_domains[r] = ds
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
        conflicts = set()
        reserve_cache = set()
        for d, us in dates.items():
            us.sort(key=lambda u: times[u][1])
            for i, a in enumerate(us):
                for b in us[i+1:]:
                    if times[b][1] >= times[a][2]:
                        break
                    if domains[a] != [rid['']] and domains[b] != [rid['']]:
                        pair = tuple(sorted((root(a), root(b))))
                        if pair not in conflicts:
                            model.add(var[a] != var[b])
                            conflicts.add(pair)
            if len(ordinary) >= RESERVA_MIN:
                for f in FRANGES:
                    active = [u for u in us if times[u][1] < f+60 and times[u][2] > f]
                    signature = tuple(sorted({root(u) for u in active}))
                    if signature in reserve_cache:
                        continue
                    reserve_cache.add(signature)
                    occupied = []
                    for r in ordinary:
                        bs = list({isroom(u, r).index: isroom(u, r) for u in active if r in domains[u]}.values())
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
        for r, us in grouped.items():
            c = model.new_int_var(0, len(corridors)-1, 'corridor')
            model.add_allowed_assignments([var[r], c], [(v, corridors[passadis(rooms[v])]) for v in sorted(group_domains[r])])
            for u in us:
                corridor_var[u] = c
        grouped_pairs = defaultdict(int)
        te_paul_pairs = defaultdict(int)
        for (a, b), count in pairs.items():
            if root(a) != root(b):
                key = tuple(sorted((root(a), root(b))))
                grouped_pairs[key] += count
                if {units[a][0].tipus, units[b][0].tipus} == {'TE', 'PAUL'}:
                    te_paul_pairs[key] += count
        for (a, b), count in grouped_pairs.items():
            if domains[a] == [rid['']] or domains[b] == [rid['']]:
                continue
            move = model.new_bool_var('move')
            model.add(var[a] != var[b]).only_enforce_if(move)
            model.add(var[a] == var[b]).only_enforce_if(move.Not())
            secondary.append(PES_MATEIXA_AULA * count * move)
            diff = model.new_bool_var('walk')
            model.add(corridor_var[a] != corridor_var[b]).only_enforce_if(diff)
            model.add(corridor_var[a] == corridor_var[b]).only_enforce_if(diff.Not())
            secondary.append(PES_PASSADIS * count * diff)
            secondary.append(PES_TRANSICIO_TE_PAUL * te_paul_pairs[a, b] * diff)
        te = defaultdict(set)
        for u, ss in units.items():
            for s in ss:
                if s.tipus == 'TE':
                    for coh in s.cohorts:
                        te[coh, s.linia].add(root(u))
        for us in te.values():
            for r in sorted({r for u in us for r in domains[u]}):
                used = model.new_bool_var('base_room')
                model.add_max_equality(used, [isroom(u, r) for u in us])
                secondary.append(PES_AULA_BASE * used)
        # One base room per student group, shared across all its activities.
        for key, us in te.items():
            choices = sorted({r for u in us for r in domains[u]})
            home = model.new_int_var_from_domain(cp_model.Domain.from_values(choices), 'home')
            home_corridor = model.new_int_var(0, len(corridors)-1, 'home_corridor')
            model.add_allowed_assignments([home, home_corridor], [(r, corridors[passadis(rooms[r])]) for r in choices])
            for u, us in grouped.items():
                ss = [s for unit in us for s in units[unit]]
                matching = [s for s in ss if key[0] in s.cohorts and s.linia == key[1] and s.tipus in ('TE', 'PAUL', 'SEM')]
                if not matching:
                    continue
                diff = model.new_bool_var('outside_home')
                if matching[0].tipus == 'TE':
                    model.add(var[u] != home).only_enforce_if(diff)
                    model.add(var[u] == home).only_enforce_if(diff.Not())
                    weight = PES_TE_FORA_BASE
                else:
                    model.add(corridor_var[u] != home_corridor).only_enforce_if(diff)
                    model.add(corridor_var[u] == home_corridor).only_enforce_if(diff.Not())
                    weight = PES_PAUL_FORA_BASE
                secondary.append(weight * len(matching) * diff)
        bound = (PES_AULA_BASE * len(rooms) * len(te)
                 + (PES_TE_FORA_BASE + PES_PAUL_FORA_BASE) * len(base.sessions) * max(1, len(te))
                 + PES_CANVI * len(base.sessions) + (PES_PASSADIS + PES_MATEIXA_AULA + PES_TRANSICIO_TE_PAUL) * sum(pairs.values()) + 1)
        model.minimize(sum(secondary) + bound*sum(routine))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(.01, min(15, (temps_s-elapsed)*.2) if merge_te else temps_s-elapsed)
        solver.parameters.num_search_workers = 2
        solver.parameters.random_seed = llavor
        # With a valid incumbent, spend the budget repairing neighbourhoods.
        solver.parameters.use_lns_only = millora_local and pista is not None and strict and not merge_te
        if pista is not None:
            for r, us in grouped.items():
                values = Counter(rid.get(pista.files[s.id].aula) for u in us for s in units[u] if s.id in pista.files)
                candidates = [v for v in values if v in group_domains[r]]
                if candidates:
                    model.add_hint(shared_vars[r], max(candidates, key=lambda v: (values[v], -v)))
        class Incumbent(cp_model.CpSolverSolutionCallback):
            def on_solution_callback(self):
                if en_solucio is not None:
                    assignment = dict(result)
                    for u, ss in units.items():
                        for s in ss:
                            assignment[s.id] = rooms[self.value(var[u])]
                    en_solucio(assignment, 'FEASIBLE')
        begin = time.monotonic()
        status = solver.solve(model, Incumbent())
        elapsed += time.monotonic()-begin
        name = solver.status_name(status)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for u, ss in units.items():
                for s in ss:
                    result[s.id] = rooms[solver.value(var[u])]
            return result, name
        if merge_te and status == cp_model.UNKNOWN and elapsed < temps_s:
            continue
        if status != cp_model.INFEASIBLE or not strict or elapsed >= temps_s:
            return {}, name
    return {}, 'UNKNOWN'

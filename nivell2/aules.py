"""Assignació d'espais amb franges decidides; regles importades del verificador."""
from collections import defaultdict, Counter
import time

from ortools.sat.python import cp_model
from nivell2.base import Proposta
from horaris.check import _espai_ok, avalua, passadis, FRANGES, RESERVA_MIN
from horaris.model import a_traslladar

PES_CANVI = 3
PES_PASSADIS = 2


def parells_seguits(units, times):
    """Parells físics per cohort, línia i subgrup; compartits pel cost i el solver."""
    agenda = defaultdict(set)
    subgroups = defaultdict(set)
    for u, ss in units.items():
        for s in ss:
            for coh in s.cohorts:
                key = coh, s.linia, times[u][0]
                sub = '*' if s.tipus == 'TE' else s.num_grup
                agenda[*key, sub].add(u)
                subgroups[key].add(sub)
    pairs = Counter()
    for key, seen in sorted(subgroups.items()):
        subs = sorted(seen - {'*'}) or ['*']
        for sub in subs:
            us = agenda.get((*key, '*'), set()) | agenda.get((*key, sub), set())
            us = sorted(us, key=lambda u: (times[u][1], units[u][0].id))
            pairs.update(zip(us, us[1:]))
    return pairs


def qualitat_aules(base, rooms, franges=None, referencia=None):
    """Criteri únic: rutina, aula base TE, cost 3·canvis + 2·passadís.

    Les dobles no necessiten espai. Els pesos 3 i 2 són els de l'especificació;
    la prioritat de rutina i aula base és lexicogràfica, sense llindars absoluts.
    """
    ref = (referencia or Proposta.de_base(base)).files
    units, patterns, te = defaultdict(list), defaultdict(Counter), defaultdict(set)
    changes = 0
    for sid, s in base.sessions.items():
        if s.sense_espai:
            continue
        units[s.unitat].append(s)
        patterns[s.activitat or sid][rooms[sid]] += 1
        changes += bool(ref[sid].aula and not a_traslladar(ref[sid].aula) and rooms[sid] != ref[sid].aula)
        if s.tipus == 'TE':
            for coh in s.cohorts:
                te[coh, s.linia].add(rooms[sid])
    times = {u: (franges or {}).get(ss[0].id, (ss[0].data, ss[0].ini)) for u, ss in units.items()}
    walks = sum(n for (a, b), n in parells_seguits(units, times).items()
                if rooms[units[a][0].id] and rooms[units[b][0].id]
                and passadis(rooms[units[a][0].id]) != passadis(rooms[units[b][0].id]))
    exceptions = sum(sum(c.values()) - max(c.values()) for c in patterns.values())
    extra = sum(max(0, len(rs) - 1) for rs in te.values())
    return exceptions, extra, PES_CANVI * changes + PES_PASSADIS * walks


def assigna_aules(base, franges, *, referencia=None, fixes=frozenset(), temps_s=300, llavor=0,
                  pista=None, en_solucio=None, agrupa_te=False, millora_local=False):
    """Retorna (id_sessio -> aula, estat CP-SAT).

    agrupa_te: prova de concentració TE; uneix grups compatibles amb les
    finestres, dominis i fixacions. Després prova també sense unions i compara amb el mateix criteri.
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

    pairs = parells_seguits(units, times)
    inherited = {
        tuple(sorted(base.sessions[sid].unitat for sid in v.sessions))
        for v in avalua(base, Proposta.de_base(base).a_files(), nomes_aules=True).violacions
        if v.regla == 'R4-AULA' and v.heretada
    }
    elapsed = 0
    best, best_key, best_status = {}, None, 'UNKNOWN'
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
        secondary, routine, home_cost = [], [], []
        for act, us in acts.items():
            us = sorted(us)
            if not strict:
                center = model.new_int_var(0, len(rooms)-1, 'routine')
                for u in us:
                    different = model.new_bool_var('exception')
                    model.add(var[u] == center).only_enforce_if(different.Not())
                    model.add(var[u] != center).only_enforce_if(different)
                    routine.append(sum((s.activitat or s.id) == act for s in units[u]) * different)
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
                    # Match the verifier's inherited room conflicts exactly; a
                    # new pair or a moved fixed class must still be constrained.
                    unchanged = all(franges[s.id] == (s.data, s.ini)
                                    and domains[u] == [rid.get(s.aula)]
                                    for u in (a, b) for s in units[u])
                    exempt = unchanged and tuple(sorted((a, b))) in inherited
                    if not exempt and domains[a] != [rid['']] and domains[b] != [rid['']]:
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
        for (a, b), count in pairs.items():
            if root(a) != root(b):
                key = tuple(sorted((root(a), root(b))))
                grouped_pairs[key] += count
        for (a, b), count in grouped_pairs.items():
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
                        te[coh, s.linia].add(root(u))
        for us in te.values():
            for r in sorted({r for u in us for r in domains[u]}):
                used = model.new_bool_var('base_room')
                model.add_max_equality(used, [isroom(u, r) for u in us])
                home_cost.append(used)
        # Encode the very same lexicographic tuple as qualitat_aules.
        secondary_bound = PES_CANVI * len(base.sessions) + PES_PASSADIS * sum(pairs.values()) + 1
        home_bound = len(rooms) * len(te) + 1
        model.minimize(sum(secondary) + secondary_bound * sum(home_cost)
                       + secondary_bound * home_bound * sum(routine))
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
            assignment = dict(result)
            for u, ss in units.items():
                for s in ss:
                    assignment[s.id] = rooms[solver.value(var[u])]
            key = qualitat_aules(base, assignment, franges, referencia)
            if best_key is None or key < best_key:
                best, best_key, best_status = assignment, key, name
                pista = Proposta.de_base(base)
                for sid, room in best.items():
                    pista.files[sid].aula = room
            if merge_te and elapsed < temps_s:
                continue
            return best, best_status
        if merge_te and status == cp_model.UNKNOWN and elapsed < temps_s:
            continue
        if status != cp_model.INFEASIBLE or not strict or elapsed >= temps_s:
            return (best, best_status) if best else ({}, name)
    return best, best_status

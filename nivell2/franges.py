"""5.2: franges CP-SAT, sense assignar aules.

assigna_franges(base, *, referencia, fixes=None, temps_s=300, llavor=0)
retorna ({id_sessio: (datetime.date, minut_inici)}, estat, excepcions).
`fixes` és un mapa opcional amb el mateix format que el resultat. Les fixades
oficials sempre conserven la partida. INFEASIBLE/UNKNOWN retornen un mapa buit;
UNKNOWN no demostra impossibilitat. Excepcions és una llista de diccionaris.
"""
from __future__ import annotations

import argparse
import datetime as dt
import itertools
from collections import defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from nivell2.base import Proposta, carrega_model, fmt, hm
from horaris.model import DIES, MATI, TARDA
from horaris.check import _alumnat_comparteix, _solapaments_de_partida

COST_CANVI = 10
COST_HORA_MORTA = 1
RESERVA = 2


def _setmana(s):
    return s.data - dt.timedelta(days=s.data.weekday())


def _referencia(s, referencia):
    a = referencia.files[s.id]
    return (dt.date.fromisoformat(a.data) if a.data else
            _setmana(s) + dt.timedelta(days=DIES.index(a.dia))), hm(a.h_ini)


def _candidats(base, s, referencia, fixes):
    if s.fixada:
        if s.id in fixes and fixes[s.id] != (s.data, s.ini):
            raise ValueError('Una sessió fixada no es pot moure')
        return [s.data.weekday() * 1440 + s.ini]
    refdata, refini = _referencia(s, referencia)
    torn = s.torn if s.torn in ('mati', 'tarda') else ('mati' if refini < MATI[1] else 'tarda')
    lo, hi = MATI if torn == 'mati' else TARDA
    out = []
    for dia in range(5):
        data = _setmana(s) + dt.timedelta(days=dia)
        if data != s.data and data in base.dies_sense_classe:
            continue
        hores = set(range(lo, hi - s.durada + 1, 30))
        if data == s.data and lo <= s.ini and s.fi <= hi:
            hores.add(s.ini)
        for ini in sorted(hores):
            aturada = any(ini < b and ini + s.durada > a for a, b in base.aturades.get(data, ()))
            heretada = data == s.data and any(s.ini < b and s.fi > a for a, b in base.aturades.get(data, ()))
            if aturada and not heretada and (data, ini) != (s.data, s.ini):
                continue
            if s.id in fixes and (data, ini) != fixes[s.id]:
                continue
            out.append(dia * 1440 + ini)
    return out


def _regles(a, b):
    rules = []
    if a.docents & b.docents:
        rules.append('R4-DOCENT')
    if _alumnat_comparteix(a, b):
        rules.append('R4-ALUMNAT')
    if a.codi == b.codi and 'PLAB' in {a.tipus, b.tipus} and {a.tipus, b.tipus} & {'TE', 'PAUL'}:
        rules.append('R4-PLAB')
    return rules


def _prepara_dobles(base):
    """Còpia de model amb unions físiques; no altera la base oficial."""
    import copy
    from nivell2.comprova_persones import parelles_dobles
    pairs, unmatched = parelles_dobles(base)
    model = copy.copy(base)
    model.sessions = {sid:copy.copy(row) for sid,row in base.sessions.items()}
    model._heretats = _solapaments_de_partida(base)
    parent = {sid:sid for sid in base.sessions}
    def root(sid):
        while parent[sid] != sid:
            parent[sid] = parent[parent[sid]]
            sid = parent[sid]
        return sid
    physical = defaultdict(list)
    for sid,row in base.sessions.items():
        physical[row.unitat].append(sid)
    for ids in list(physical.values()) + [[sid,*partners] for sid,partners in pairs.items()]:
        for sid in ids[1:]:
            parent[root(sid)] = root(ids[0])
    components = defaultdict(list)
    for sid in parent:
        components[root(sid)].append(sid)
    frozen = 0
    model._dobles_unitats = {}
    model._parelles = pairs
    for key,ids in components.items():
        rows = [model.sessions[sid] for sid in ids]
        double = any(r.sense_espai for r in rows)
        locked = any(r.fixada or r.tipus == 'PLAB' or (r.sense_espai and r.id not in pairs) for r in rows)
        host = next((r for r in rows if not r.sense_espai),rows[0])
        for row in rows:
            model._dobles_unitats[row.unitat] = key
            if double and locked:
                row.fixada = row.fixada or 'vincle doble immobilitzat'
            if row.sense_espai and not locked:
                row.torn = host.torn
        frozen += double and locked
    return model, {'dobles_aparellades':len(pairs),'dobles_sense_parella':unmatched,
                   'unitats_dobles_immobils':frozen}


def _problema(base, referencia, fixes):
    """Precalcula parells físics per setmana, amb les exempcions oficials."""
    units, weeks = defaultdict(list), defaultdict(list)
    for s in base.sessions.values():
        units[s.unitat].append(s)
    inherited = getattr(base,"_heretats",None)
    if inherited is None:
        inherited = _solapaments_de_partida(base)
    edges = []
    for u, rows in units.items():
        weeks[_setmana(rows[0])].append(u)
    for us in weeks.values():
        index = defaultdict(set)
        for u in us:
            for s in units[u]:
                for d in s.docents:
                    index['D', d].add(u)
                for c in s.cohorts:
                    index['E', c].add(u)
                index['P', s.codi].add(u)
        pairs = set()
        for group in index.values():
            pairs.update(itertools.combinations(sorted(group), 2))
        for u, v in sorted(pairs):
            links = getattr(base,'_dobles_unitats',{})
            if links.get(u,u) == links.get(v,v):
                continue
            if any(any((r, tuple(sorted((a.id, b.id)))) not in inherited
                       and not (a.fixada and b.fixada) for r in _regles(a, b))
                   for a in units[u] for b in units[v]):
                edges.append((u, v))
    # Compartides entre activitats: una sola variable de rutina per component.
    parent = {s.activitat or s.id: s.activitat or s.id for s in base.sessions.values()}
    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for rows in units.values():
        for s in rows[1:]:
            parent[root(s.activitat or s.id)] = root(rows[0].activitat or rows[0].id)
    for sid,partners in getattr(base,'_parelles',{}).items():
        if sid in base.sessions:
            for partner in partners:
                if partner in base.sessions:
                    a,b = base.sessions[sid],base.sessions[partner]
                    parent[root(a.activitat or a.id)] = root(b.activitat or b.id)
    groups = {u: root(rows[0].activitat or rows[0].id) for u, rows in units.items()}
    return units, weeks, edges, groups


def _colls_capacitat(base, units, weeks, selected, candidates):
    """Certificats de demanda fixa superior a l'oferta, mai inferits d'UNKNOWN."""
    rooms = [a for a in base.aules.values() if a.tipus in ('Aules docents', 'Seminaris')]
    reports = []
    for week, us in weeks.items():
        buckets = defaultdict(list)
        for u in us:
            if u not in selected or selected[u][0] != 'f':
                continue
            rows = [r for r in units[u] if not r.sense_espai and r.tipus != 'PLAB']
            if not rows:
                continue
            start = next(iter(candidates[selected[u]]))
            end = start + max(r.durada for r in rows)
            for day in range(5):
                for hour in range(MATI[0], TARDA[1], 60):
                    if start < day*1440+hour+60 and end > day*1440+hour:
                        buckets[day,hour].append(sum(r.alumnes for r in rows))
        for (day,hour), sizes in buckets.items():
            for threshold in [-1]+sorted({a.capacitat for a in rooms}):
                demand = sum(n > threshold for n in sizes)
                supply = max(0,len(rooms)-RESERVA) if threshold == -1 else sum(a.capacitat>threshold for a in rooms)
                if demand > supply:
                    reports.append({'tipus':'capacitat_obstacles',
                                    'data':(week+dt.timedelta(days=day)).isoformat(),
                                    'h_ini':fmt(hour), 'mes_de_alumnes':threshold,
                                    'demanda':demand, 'oferta':supply})
    return reports


def _resol_torn(base, units, weeks, edges, groups, movibles, current, referencia,
                fixes, shift, deadline, llavor, *, reparacio=False, limits_capacitat=None, setmana_completa=False, torn_tou=False, ignora_calendari=False):
    """Un model compacte: només les activitats movibles tenen variables."""
    import time
    lo, hi = shift
    limits_capacitat = limits_capacitat or {}
    m = cp_model.CpModel()
    candidates = defaultdict(set)
    selected = {}
    links = getattr(base,'_dobles_unitats',{})
    moving_links = {links.get(u,u) for u in movibles}
    for u, rows in units.items():
        s = rows[0]
        required = MATI if s.torn == 'mati' else TARDA
        mobile = groups[u] in movibles and not any(r.fixada for r in rows)
        if reparacio:
            mobile = links.get(u,u) in moving_links and not any(r.fixada for r in rows)
        if mobile and required != shift and not setmana_completa:
            continue
        key = ('u', getattr(base,'_dobles_unitats',{}).get(u,u)) if reparacio else ('a', groups[u])
        if mobile:
            selected[u] = key
            domain = set.intersection(*(set(_candidats(base, r, referencia, fixes)) for r in rows)) if reparacio and not ignora_calendari else {
                d*1440+t for d in range(5) for t in range(lo, hi-max(r.durada for r in rows)+1,30)}
            if torn_tou:
                original = s.data.weekday()*1440+s.ini
                from horaris.check import _dins_finestra
                if _dins_finestra(s.ini,s.fi) and all(r.id not in fixes or fixes[r.id] == (r.data,r.ini) for r in rows):
                    domain.add(original)
            if not reparacio or ignora_calendari:
                for r in rows:
                    original = r.data.weekday()*1440+r.ini
                    if lo <= r.ini and r.fi <= hi:
                        domain.add(original)
                # Explicit fixes remain hard; individual calendar repair comes later.
                for r in rows:
                    if r.id in fixes:
                        date, minute = fixes[r.id]
                        domain &= {(date-_setmana(r)).days*1440+minute}
            if key in candidates:
                candidates[key] &= domain
            else:
                candidates[key] = domain
        else:
            date, minute = current[s.id]
            if any(r.id in fixes and fixes[r.id] != (date,minute) for r in rows):
                return None, 'INFEASIBLE'
            # Fixed obstacles crossing the split must appear in both models.
            if minute < hi and minute+max(r.durada for r in rows) > lo:
                selected[u] = ('f', u)
                candidates[('f', u)] = {date.weekday()*1440+minute}
    if any(not ds for ds in candidates.values()):
        assigna_franges.estadistiques['causa'] = 'domini_buit'
        return None, 'INFEASIBLE'
    variables, durations, cost, dayscost = {}, {}, [], []
    for key, ds in candidates.items():
        variables[key] = m.new_int_var_from_domain(cp_model.Domain.from_values(sorted(ds)), str(key))
    for u, key in selected.items():
        durations[u] = max(s.durada for s in units[u])
    for key, x in variables.items():
        if key[0] == 'f':
            continue
        us = [u for u, k in selected.items() if k == key]
        originals = {current[units[u][0].id][0].weekday()*1440+current[units[u][0].id][1] for u in us}
        ref = min(originals)
        hint = min(candidates[key], key=lambda v:(v//1440 != ref//1440,abs(v%1440-ref%1440)))
        m.add_hint(x, hint)
        # One change per activity, then same-day preference as a tie break.
        changed = m.new_bool_var('canvi_activitat')
        m.add(x == ref).only_enforce_if(changed.Not())
        m.add(x != ref).only_enforce_if(changed)
        cost.append(changed)
        day = m.new_int_var(0,4,'dia')
        m.add_division_equality(day,x,1440)
        dc = m.new_bool_var('canvi_dia')
        m.add(day == ref//1440).only_enforce_if(dc.Not())
        m.add(day != ref//1440).only_enforce_if(dc)
        dayscost.append(dc)
    seen = set()
    for u, v in edges:
        if u not in selected or v not in selected:
            continue
        a, b = selected[u], selected[v]
        if a[0] == b[0] == 'f':
            continue
        pair = (a,b,durations[u],durations[v])
        if pair in seen:
            continue
        seen.add(pair)
        if a == b:
            assigna_franges.estadistiques['causa'] = 'conflicte_intern'
            return None, 'INFEASIBLE'
        before = m.new_bool_var('ordre')
        m.add(variables[a]+durations[u] <= variables[b]).only_enforce_if(before)
        m.add(variables[b]+durations[v] <= variables[a]).only_enforce_if(before.Not())
    bottlenecks = _colls_capacitat(base,units,weeks,selected,candidates)
    if bottlenecks:
        assigna_franges.estadistiques['colls_capacitat'] = bottlenecks
        return None, 'INFEASIBLE'
    rooms = [a for a in base.aules.values() if a.tipus in ('Aules docents','Seminaris')]
    # The rounded interval can be reused in every week with the same activity.
    intervals = {}
    patterns = set()
    for us in weeks.values():
        entries = []
        for u in us:
            if u not in selected:
                continue
            rows = [s for s in units[u] if not s.sense_espai and s.tipus != 'PLAB']
            if not rows:
                continue
            key = (selected[u], durations[u], sum(s.alumnes for s in rows))
            entries.append(key)
            if key not in intervals:
                x = variables[selected[u]]
                start = m.new_int_var(0,120,'cubell_inici')
                end = m.new_int_var(0,120,'cubell_fi')
                length = m.new_int_var(1,24,'cubells')
                m.add_division_equality(start,x-MATI[0],60)
                m.add_division_equality(end,x+durations[u]-MATI[0]+59,60)
                m.add(length==end-start)
                intervals[key] = m.new_interval_var(start,length,end,'capacitat')
        pattern = tuple(sorted(entries))
        if pattern in patterns or not entries:
            continue
        patterns.add(pattern)
        for threshold in [-1]+sorted({a.capacitat for a in rooms}):
            relevant = [intervals[k] for k in entries if k[2]>threshold]
            available = max(0,len(rooms)-RESERVA) if threshold == -1 else sum(a.capacitat>threshold for a in rooms)
            available = min(available, limits_capacitat.get(threshold, available))
            if relevant:
                m.add_cumulative(relevant,[1]*len(relevant),available)
    # Hall constraints for restricted equipment (e.g. only two computer rooms).
    # Size-only cuts cannot see these bottlenecks. Include fixed sessions too.
    from horaris.check import _espai_ok
    eligible = {}
    for u in selected:
        rows = [r for r in units[u] if not r.sense_espai]
        if not rows:
            continue
        allowed = set(base.aules)
        for r in rows:
            allowed &= {a for a in base.aules if _espai_ok(base,r,a)}
        n = sum(r.alumnes for r in rows)
        allowed = {a for a in allowed if base.aules[a].capacitat >= n}
        fixed = {r.aula for r in rows if r.tipus == 'PLAB' or (r.fixada and r.aula)}
        if fixed:
            allowed = fixed
        if allowed and '' not in allowed:
            eligible[u] = frozenset(allowed)
    resources = sorted(set(eligible.values()),key=lambda r:tuple(sorted(r)))
    patterns = set()
    for us in weeks.values():
        for resource in resources:
            relevant = [u for u in us if u in eligible and eligible[u] <= resource]
            if len(relevant) <= len(resource):
                continue
            pattern = (resource,tuple(sorted((selected[u],durations[u]) for u in relevant)))
            if pattern in patterns:
                continue
            patterns.add(pattern)
            tasks = [m.new_fixed_size_interval_var(variables[selected[u]],durations[u],'equipament') for u in relevant]
            m.add_cumulative(tasks,[1]*len(tasks),len(resource))
    penalties = []
    if torn_tou:
        from horaris.check import _torn_ok
        for u,key in selected.items():
            rows = units[u]
            if key[0] != 'f' and any(_torn_ok(r.torn,r.ini,r.fi) is False for r in rows):
                original = rows[0].data.weekday()*1440+rows[0].ini
                exc = m.new_bool_var('excepcio_R1')
                m.add(variables[key] == original).only_enforce_if(exc)
                m.add(variables[key] != original).only_enforce_if(exc.Not())
                penalties.append(len(rows)*exc)
    secondary_bound = COST_CANVI*(len(dayscost)+1)*len(cost)+len(dayscost)+1
    m.minimize(secondary_bound*sum(penalties)+COST_CANVI*(len(dayscost)+1)*sum(cost)+sum(dayscost))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(.001, deadline-time.monotonic())
    solver.parameters.num_workers = 2
    solver.parameters.random_seed = llavor
    solver.parameters.stop_after_first_solution = not torn_tou
    status = solver.solve(m)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        assigna_franges.estadistiques['causa'] = 'solver'
        return None, solver.status_name(status)
    out = dict(current)
    for u,key in selected.items():
        value = solver.value(variables[key])
        for s in units[u]:
            out[s.id] = (_setmana(s)+dt.timedelta(days=value//1440),value%1440)
    return out, solver.status_name(status)


def assigna_franges(base, *, referencia, fixes=None, temps_s=300, llavor=0, limits_capacitat=None, permet_excepcions_torn=False):
    """Primera passada per activitat/torn; reparació local de calendari després.

    `permet_excepcions_torn` autoritza exclusivament W14/2027, després d'un
    INFEASIBLE conjunt de tota la setmana: l'única alternativa fora de torn
    és la franja original. `limits_capacitat` és llindar d'alumnes -> màxim
    per cubell horari (-1: total). Les proves i el mínim trobat es registren.
    Contracte del mòdul. `assigna_franges.estadistiques` registra els temps i
    recomptes de l'última crida (ús seqüencial). La passada opcional d'hores
    mortes s'omet per prioritzar el lliurament de la primera solució vàlida.
    """
    import time
    from horaris.check import _torn_ok, _dins_finestra
    begin = time.monotonic()
    deadline = begin+temps_s
    fixes = fixes or {}
    if temps_s <= 0 or set(fixes)-set(base.sessions):
        raise ValueError('temps invàlid o fixes desconegudes')
    for sid, value in fixes.items():
        s = base.sessions[sid]
        if s.fixada and value != (s.data,s.ini):
            raise ValueError('Una sessió fixada no es pot moure')
    base, double_stats = _prepara_dobles(base)
    units,weeks,edges,groups = _problema(base,referencia,fixes)
    current = {s.id:_referencia(s,referencia) for s in base.sessions.values()}
    current.update(fixes)
    for s in base.sessions.values():
        if s.fixada:
            current[s.id] = (s.data,s.ini)
    mobile = {groups[s.unitat] for s in base.sessions.values() if not s.fixada and
              (_torn_ok(s.torn,s.ini,s.fi) is False or not _dins_finestra(s.ini,s.fi))}
    stats = {'components_oberts':len(mobile),'passada1_s':0,'reparacio_s':0,'passada2_s':0}
    stats.update(double_stats)
    assigna_franges.estadistiques = stats
    for shift in (MATI,TARDA):
        opened = set(mobile)
        for level in range(3):
            solution,state = _resol_torn(base,units,weeks,edges,groups,opened,current,referencia,
                                         fixes,shift,deadline,llavor,limits_capacitat=limits_capacitat)
            if solution is not None:
                current = solution
                break
            if state != 'INFEASIBLE' or time.monotonic() >= deadline:
                return {},state,[]
            affected = [s for s in base.sessions.values() if groups[s.unitat] in opened]
            docents = set().union(*(s.docents for s in affected)) if affected else set()
            cohorts = set().union(*(set(s.cohorts) for s in affected)) if affected else set()
            opened.update(groups[s.unitat] for s in base.sessions.values()
                          if not s.fixada and (set(s.cohorts)&cohorts or (level == 0 and s.docents&docents)))
        else:
            # Routine is soft: retry independent weeks before declaring failure.
            import copy
            for week, us_list in sorted(weeks.items()):
                us = set(us_list)
                sub = copy.copy(base)
                sub.sessions = {r.id:r for u in us for r in units[u]}
                sub.ordre = list(sub.sessions)
                repaired,state = _resol_torn(sub,{u:units[u] for u in us},{week:us_list},
                    [(u,v) for u,v in edges if u in us and v in us],groups,us,current,
                    referencia,fixes,shift,deadline,llavor,reparacio=True,
                    limits_capacitat=limits_capacitat,ignora_calendari=True)
                if repaired is None:
                    return {},state,stats.get('colls_capacitat',[])
                current = repaired
            stats['rutina_reparada_per_setmanes'] = True
    stats['passada1_s'] = time.monotonic()-begin
    repair_begin = time.monotonic()
    invalid = set()
    for u,rows in units.items():
        for s in rows:
            data,minute = current[s.id]
            if data.weekday()*1440+minute not in _candidats(base,s,referencia,fixes):
                invalid.add(u)
    routine = dict(current)
    for shift in (MATI,TARDA):
        if invalid:
            solution,state = _resol_torn(base,units,weeks,edges,groups,invalid,current,referencia,
                                         fixes,shift,deadline,llavor,reparacio=True,limits_capacitat=limits_capacitat)
            if solution is None and state == 'INFEASIBLE':
                affected_weeks = {_setmana(units[u][0]) for u in invalid}
                expanded = set(invalid)
                for u,v in edges:
                    if u in invalid or v in invalid:
                        expanded.update((u,v))
                types = {base.aules[s.aula].tipus for u in invalid for s in units[u]
                         if s.aula in base.aules and base.aules[s.aula].tipus == 'Aules informàtiques'}
                expanded.update(u for u,rows in units.items() if _setmana(rows[0]) in affected_weeks
                                and any(s.aula in base.aules and base.aules[s.aula].tipus in types for s in rows))
                solution,state = _resol_torn(base,units,weeks,edges,groups,expanded,current,referencia,
                    fixes,shift,deadline,llavor,reparacio=True,limits_capacitat=limits_capacitat)
            if solution is None and state == 'INFEASIBLE':
                # Last local circle: solve affected real weeks independently.
                # Avoid reopening the whole semester in one large model.
                import copy
                solution = dict(current)
                for week in sorted({_setmana(units[u][0]) for u in invalid
                                    if (MATI if units[u][0].torn == 'mati' else TARDA) == shift}):
                    us = set(weeks[week])
                    sub = copy.copy(base)
                    sub.sessions = {s.id:s for u in us for s in units[u]}
                    sub.ordre = list(sub.sessions)
                    repaired,state = _resol_torn(sub,{u:units[u] for u in us}, {week:weeks[week]},
                        [(u,v) for u,v in edges if u in us and v in us], groups, us,
                        solution,referencia,fixes,shift,deadline,llavor,reparacio=True,
                        limits_capacitat=limits_capacitat)
                    if repaired is None and state == 'INFEASIBLE' and permet_excepcions_torn and week == dt.date(2027,4,5):
                        hard_begin = time.monotonic()
                        repaired,hard_state = _resol_torn(sub,{u:units[u] for u in us}, {week:weeks[week]},
                            [(u,v) for u,v in edges if u in us and v in us], groups, us,
                            solution,referencia,fixes,(MATI[0],TARDA[1]),deadline,llavor,
                            reparacio=True,limits_capacitat=limits_capacitat,setmana_completa=True)
                        proof = {'setmana':week.isoformat(),'dur':hard_state,'dur_s':time.monotonic()-hard_begin}
                        if repaired is None and hard_state == 'INFEASIBLE':
                            soft_begin = time.monotonic()
                            repaired,state = _resol_torn(sub,{u:units[u] for u in us}, {week:weeks[week]},
                                [(u,v) for u,v in edges if u in us and v in us], groups, us,
                                solution,referencia,fixes,(MATI[0],TARDA[1]),min(deadline,soft_begin+90),llavor,
                                reparacio=True,limits_capacitat=limits_capacitat,setmana_completa=True,torn_tou=True)
                            proof.update(tou=state,tou_s=time.monotonic()-soft_begin)
                            if repaired is not None:
                                from horaris.check import _torn_ok
                                proof['sessions'] = [s.id for s in sub.sessions.values() if not s.fixada and
                                    _torn_ok(s.torn,repaired[s.id][1],repaired[s.id][1]+s.durada) is False]
                                proof['nombre'] = len(proof['sessions'])
                                invalid.difference_update(us)
                        stats.setdefault('proves_torn',[]).append(proof)
                    if repaired is None:
                        stats['setmana_reparacio_fallida'] = week.isoformat()
                        stats['torn_reparacio_fallit'] = shift
                        solution = None
                        break
                    solution = repaired
            if solution is None:
                return {},state,[]
            current = solution
    notes = [{'id_sessio':s.id,'data':current[s.id][0].isoformat(),'minut_inici':current[s.id][1],
              'motiu':('calendari: festiu, no lectiu o aturada' if s.unitat in invalid else 'reparació local de la setmana per fer lloc a una excepció de calendari')}
             for s in base.sessions.values() if current[s.id] != routine[s.id]]
    stats['reparacio_s'] = time.monotonic()-repair_begin
    stats['total_s'] = time.monotonic()-begin
    stats['sessions_canviades'] = sum(current[s.id] != _referencia(s,referencia) for s in base.sessions.values())
    stats['activitats_canviades'] = len({s.activitat or s.id for s in base.sessions.values()
                                        if current[s.id] != _referencia(s,referencia)})
    stats['excepcions_festiu'] = len(notes)
    # These local models do not prove global optimality with frozen activities.
    return current, 'FEASIBLE', notes


def _hores_mortes(m, base, units, starts, weeks):
    """Minuts entre sessions consecutives, amb els subgrups del verificador.

    L'ordre és per inici i id, també quan hi ha solapaments heretats.
    No compta el migdia ni replica una teoria per subgrups absents aquell dia.
    """
    costs = []
    days, minutes = {}, {}
    for u, x in starts.items():
        days[u] = m.new_int_var(0, 4, 'dia_agenda')
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
            value = m.new_int_var(0, 7200, 'candidat_seguent')
            m.add(value == starts[v]).only_enforce_if(later)
            m.add(value == 7200).only_enforce_if(later.Not())
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
            if len(members) < 2:
                continue
            all_practice = set().union(*(v for k, v in groups.items() if k[:2] == key[:2]))
            for u in members:
                following = m.new_int_var(0, 7200, 'seguent')
                m.add_min_equality(following, [later_start(u, v) for v in members if v != u])
                nextday = m.new_int_var(0, 5, 'dia_seguent')
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
                    present = [same_day(u, v) for v in (all_practice if key[2] == '*' else practice)]
                    if present:
                        any_present = m.new_bool_var('practiques_aquell_dia')
                        m.add_max_equality(any_present, present)
                        m.add(active == (1 - any_present if key[2] == '*' else any_present))
                    else:
                        m.add(active == (1 if key[2] == '*' else 0))
                count = m.new_bool_var('compta_buit')
                m.add_bool_and([same, shift, active]).only_enforce_if(count)
                m.add_bool_or([same.Not(), shift.Not(), active.Not()]).only_enforce_if(count.Not())
                gap = m.new_int_var(0, 7200, 'buit_positiu')
                m.add_max_equality(gap, [0, following-starts[u]-duration])
                cost = m.new_int_var(0, 1440, 'minuts_morts')
                m.add(cost == gap).only_enforce_if(count)
                m.add(cost == 0).only_enforce_if(count.Not())
                costs.append(cost)
    return costs


def proposta_franges(base, referencia, franges):
    """Aplica les franges conservant les aules de la referència."""
    import copy
    p = copy.deepcopy(referencia)
    for sid, (data, ini) in franges.items():
        p.files[sid].dia = DIES[data.weekday()]
        p.files[sid].h_ini = fmt(ini)
        if p.files[sid].data:
            p.files[sid].data = data.isoformat()
        if base.sessions[sid].aula == 'B3/0021' and (data, ini) != (base.sessions[sid].data, base.sessions[sid].ini):
            p.files[sid].aula = ''
    return p


def main():
    import time
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sortida', type=Path, required=True)
    parser.add_argument('--temps', type=float, default=300)
    args = parser.parse_args()
    base = carrega_model()
    ref = Proposta.de_base(base)
    begin = time.monotonic()
    result, state, notes = assigna_franges(base, referencia=ref, temps_s=args.temps)
    print(f'{state}; {time.monotonic()-begin:.1f} s; {len(result)} sessions assignades')
    if result:
        proposta_franges(base, ref, result).escriu(args.sortida)
        print('Canvis de franja:', sum(result[s.id] != (s.data, s.ini) for s in base.sessions.values()))
    import json
    detail = Path(__file__).resolve().parents[1]/'resultats/nivell2/5.2/franges-detall.json'
    detail.parent.mkdir(parents=True,exist_ok=True)
    detail.write_text(json.dumps({'estadistiques':assigna_franges.estadistiques,'excepcions':notes},ensure_ascii=False,indent=2))
    print('Excepcions:', len(notes))
    return 0 if result else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        import traceback
        target = Path(__file__).resolve().parents[1]/'resultats/nivell2/5.2'
        target.mkdir(parents=True,exist_ok=True)
        (target/'error-franges.txt').write_text(traceback.format_exc(),encoding='utf-8')
        print('Errors d’execució: 1; detall desat fora de git')
        raise SystemExit(2)

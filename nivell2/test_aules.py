"""Fixtures sintètiques petites, sense carregar dades del repte."""
import datetime as dt
from nivell2.base import Base, Sessio, Proposta
from horaris.model import Aula
from nivell2.aules import assigna_aules


def session(sid, *, activity='', room='', students=20, shared='', start=510, day=2, **kw):
    return Sessio(sid, sid, 'TE', 'TE/908', dt.date(2027, 2, day), 'M', start, 60,
                  students, room, (), 'mati', '', frozenset(), shared, activity, **kw)


def base(*ss, sizes=(30, 60, 100, 100)):
    rooms = {f'Q1/100{i}': Aula(f'Q1/100{i}', 'Q1', 'Aules docents', n) for i, n in enumerate(sizes)}
    return Base({s.id: s for s in ss}, rooms, [s.id for s in ss])


def solve(b, **kw):
    return assigna_aules(b, {s.id: (s.data, s.ini) for s in b.sessions.values()}, temps_s=2, **kw)


def test_capacity_overlap_and_routine():
    b = base(session('a', activity='x', students=50), session('b', activity='x', students=50, day=9), session('c'))
    rooms, status = solve(b)
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['a'] == rooms['b'] != rooms['c']
    assert b.aules[rooms['a']].capacitat >= 50


def test_shared_sum_and_same_room():
    b = base(session('a', shared='s', students=35), session('b', shared='s', students=35))
    rooms, _ = solve(b)
    assert rooms['a'] == rooms['b']
    assert b.aules[rooms['a']].capacitat >= 70


def test_hourly_reserve_counts_distinct_rooms():
    b = base(session('a'), session('b'), session('c', start=540))
    assert solve(b)[1] == 'INFEASIBLE'


def test_fixed_reference_and_double():
    b = base(session('a'), session('d', sense_espai=True))
    ref = Proposta.de_base(b)
    ref.files['a'].aula = 'Q9/5003'
    rooms, _ = solve(b, referencia=ref, fixes={'a'})
    assert rooms == {'a': 'Q9/5003', 'd': ''}


def test_missing_slots_is_error():
    try:
        assigna_aules(base(session('a')), {})
    except ValueError:
        pass
    else:
        raise AssertionError('cal rebutjar les franges incompletes')


def test_routine_can_break_for_hard_constraints():
    b = base(session('a', activity='x', room='Q9/5001'), session('b', activity='x', room='Q9/5002', day=9))
    rooms, status = solve(b, fixes={'a', 'b'})
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['a'] != rooms['b']


def test_unassigned_plab_does_not_occupy_room():
    a, b = session('a'), session('b')
    a.tipus = b.tipus = 'PLAB'
    a.fixada = b.fixada = 'R7: PLAB'
    rooms, status = solve(base(a, b))
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms == {'a': '', 'b': ''}


def test_closure_forces_routine_exception():
    from horaris.model import Tancament
    b = base(session('a', activity='x'), session('b', activity='x', day=9), sizes=(30, 30))
    b.tancaments = [Tancament('Q9/5001', dt.date(2027, 2, 2), dt.date(2027, 2, 2)),
                    Tancament('Q9/5002', dt.date(2027, 2, 9), dt.date(2027, 2, 9))]
    # Seminars do not enter the ordinary-room reserve.
    b.aules = {a: Aula(a, x.edifici, 'Seminaris', x.capacitat) for a, x in b.aules.items()}
    rooms, status = solve(b)
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['a'] == 'Q9/5002' and rooms['b'] == 'Q9/5001'


def test_student_home_beats_original_rooms_and_uses_hint():
    a = session('a', room='Q9/5001')
    b = session('b', room='Q9/5002', start=570)
    c = session('c', room='Q9/5007', start=630)
    c.tipus = 'PAUL'
    c.grup = 'PAUL/900'
    for s in (a, b, c):
        s.cohorts = ('G:1r',)
    data = base(a, b, c)
    data.aules['Q9/5007'] = Aula('Q9/5007', 'Q2', 'Aules docents', 30)
    hint = Proposta.de_base(data)
    incumbents = []
    rooms, status = solve(data, pista=hint, en_solucio=lambda r, st: incumbents.append((r, st)))
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['a'] == rooms['b'] == rooms['c']
    # Parallel LNS can return a different tied optimum than its last callback.
    assert incumbents and any(len(set(r.values())) == 1 for r, _ in incumbents)


def test_fixed_te_prevents_impossible_home_but_stays_valid():
    a = session('a', room='Q9/5001')
    b = session('b', start=570)
    a.fixada = 'R1: fixed'
    a.cohorts = b.cohorts = ('G:1r',)
    rooms, _ = solve(base(a, b))
    assert rooms['a'] == rooms['b'] == 'Q9/5001'


def test_concentration_retries_if_global_conflict():
    a, b, c, d = (session('a'), session('b', start=570),
                   session('c', start=570), session('d', start=630))
    a.cohorts = b.cohorts = ('A:1r',)
    c.cohorts = d.cohorts = ('B:1r',)
    a.aula = d.aula = 'Q9/5001'
    a.fixada = d.fixada = 'R1: fixed'
    # Each group alone can use that room, but b/c coincide. Global unions
    # are infeasible, so the ordinary activity model must repair one group.
    rooms, status = solve(base(a, b, c, d), agrupa_te=True)
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['a'] == rooms['d'] == 'Q9/5001'
    assert rooms['b'] != rooms['c']


def test_hint_from_old_slots_can_be_repaired():
    b = base(session('a'), session('b'))
    hint = Proposta.de_base(b)
    hint.files['a'].aula = hint.files['b'].aula = 'Q9/5001'
    rooms, status = solve(b, pista=hint)
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['a'] != rooms['b']


if __name__ == '__main__':
    import time
    start = time.monotonic()
    tests = [v for k, v in list(globals().items()) if k.startswith('test_')]
    for test in tests:
        test()
    print(f'{len(tests)} proves OK en {time.monotonic()-start:.3f} s')

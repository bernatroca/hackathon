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


if __name__ == '__main__':
    import time
    start = time.monotonic()
    tests = [v for k, v in list(globals().items()) if k.startswith('test_')]
    for test in tests:
        test()
    print(f'{len(tests)} proves OK en {time.monotonic()-start:.3f} s')

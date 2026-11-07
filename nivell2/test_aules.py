"""Fixtures sintètiques petites, sense carregar dades del repte."""
import datetime as dt
from nivell2.base import Base, Sessio, Proposta
from horaris.model import Aula
from nivell2.aules import assigna_aules


def session(sid, *, activity='', room='', students=20, shared='', start=510, day=2, **kw):
    return Sessio(sid, '100001', 'TE', 'TE/81', dt.date(2027, 2, day), 'M', start, 60,
                  students, room, (), 'mati', '', frozenset(), shared, activity, **kw)


def base(*ss, sizes=(30, 60, 100, 100)):
    rooms = {f'Q9/{i+1:04d}': Aula(f'Q9/{i+1:04d}', 'Q9', 'Aules docents', n) for i, n in enumerate(sizes)}
    return Base({s.id: s for s in ss}, rooms, [s.id for s in ss])


def solve(b, **kw):
    return assigna_aules(b, {s.id: (s.data, s.ini) for s in b.sessions.values()}, temps_s=2, **kw)


def test_capacity_overlap_and_routine():
    b = base(session('S90001', activity='A9001', students=50), session('S90002', activity='A9001', students=50, day=9), session('S90003'))
    rooms, status = solve(b)
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['S90001'] == rooms['S90002'] != rooms['S90003']
    assert b.aules[rooms['S90001']].capacitat >= 50


def test_shared_sum_and_same_room():
    b = base(session('S90001', shared='C90001', students=35), session('S90002', shared='C90001', students=35))
    rooms, _ = solve(b)
    assert rooms['S90001'] == rooms['S90002']
    assert b.aules[rooms['S90001']].capacitat >= 70


def test_hourly_reserve_counts_distinct_rooms():
    b = base(session('S90001'), session('S90002'), session('S90003', start=540))
    assert solve(b)[1] == 'INFEASIBLE'


def test_fixed_reference_and_double():
    b = base(session('S90001'), session('S90004', sense_espai=True))
    ref = Proposta.de_base(b)
    ref.files['S90001'].aula = 'Q9/0003'
    rooms, _ = solve(b, referencia=ref, fixes={'S90001'})
    assert rooms == {'S90001': 'Q9/0003', 'S90004': ''}


def test_missing_slots_is_error():
    try:
        assigna_aules(base(session('S90001')), {})
    except ValueError:
        pass
    else:
        raise AssertionError('cal rebutjar les franges incompletes')


def test_routine_can_break_for_hard_constraints():
    b = base(session('S90001', activity='A9001', room='Q9/0001'), session('S90002', activity='A9001', room='Q9/0002', day=9))
    rooms, status = solve(b, fixes={'S90001', 'S90002'})
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['S90001'] != rooms['S90002']


def test_unassigned_plab_does_not_occupy_room():
    a, b = session('S90001'), session('S90002')
    a.tipus = b.tipus = 'PLAB'
    a.fixada = b.fixada = 'R7: PLAB'
    rooms, status = solve(base(a, b))
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms == {'S90001': '', 'S90002': ''}


def test_closure_forces_routine_exception():
    from horaris.model import Tancament
    b = base(session('S90001', activity='A9001'), session('S90002', activity='A9001', day=9), sizes=(30, 30))
    b.tancaments = [Tancament('Q9/0001', dt.date(2027, 2, 2), dt.date(2027, 2, 2)),
                    Tancament('Q9/0002', dt.date(2027, 2, 9), dt.date(2027, 2, 9))]
    # Seminars do not enter the ordinary-room reserve.
    b.aules = {a: Aula(a, x.edifici, 'Seminaris', x.capacitat) for a, x in b.aules.items()}
    rooms, status = solve(b)
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['S90001'] == 'Q9/0002' and rooms['S90002'] == 'Q9/0001'


def test_student_home_beats_original_rooms_and_uses_hint():
    a = session('S90001', room='Q9/0001')
    b = session('S90002', room='Q9/0002', start=570)
    c = session('S90003', room='Q9/1001', start=630)
    c.tipus = 'PAUL'
    c.grup = 'PAUL/811'
    for s in (a, b, c):
        s.cohorts = ('G:1r',)
    data = base(a, b, c)
    data.aules['Q9/1001'] = Aula('Q9/1001', 'Q9', 'Aules docents', 30)
    hint = Proposta.de_base(data)
    incumbents = []
    rooms, status = solve(data, pista=hint, en_solucio=lambda r, st: incumbents.append((r, st)))
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['S90001'] == rooms['S90002'] == rooms['S90003']
    # Parallel LNS can return a different tied optimum than its last callback.
    assert incumbents and any(len(set(r.values())) == 1 for r, _ in incumbents)


def test_fixed_te_prevents_impossible_home_but_stays_valid():
    a = session('S90001', room='Q9/0001')
    b = session('S90002', start=570)
    a.fixada = 'R1: fixed'
    a.cohorts = b.cohorts = ('G:1r',)
    rooms, _ = solve(base(a, b))
    assert rooms['S90001'] == rooms['S90002'] == 'Q9/0001'


def test_concentration_retries_if_global_conflict():
    a, b, c, d = (session('S90001'), session('S90002', start=570),
                   session('S90003', start=570), session('S90004', start=630))
    a.cohorts = b.cohorts = ('A:1r',)
    c.cohorts = d.cohorts = ('B:1r',)
    a.aula = d.aula = 'Q9/0001'
    a.fixada = d.fixada = 'R1: fixed'
    # Each group alone can use that room, but b/c coincide. Global unions
    # are infeasible, so the ordinary activity model must repair one group.
    rooms, status = solve(base(a, b, c, d), agrupa_te=True)
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['S90001'] == rooms['S90004'] == 'Q9/0001'
    assert rooms['S90002'] != rooms['S90003']


def test_hint_from_old_slots_can_be_repaired():
    b = base(session('S90001'), session('S90002'))
    hint = Proposta.de_base(b)
    hint.files['S90001'].aula = hint.files['S90002'].aula = 'Q9/0001'
    rooms, status = solve(b, pista=hint)
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms['S90001'] != rooms['S90002']


if __name__ == '__main__':
    import time
    start = time.monotonic()
    tests = [v for k, v in list(globals().items()) if k.startswith('test_')]
    for test in tests:
        test()
    print(f'{len(tests)} proves OK en {time.monotonic()-start:.3f} s')

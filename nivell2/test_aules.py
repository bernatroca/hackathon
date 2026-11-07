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
    assert rooms['S90001'] == rooms['S90002']
    # Restoring PAUL would cost 3, while its corridor transition costs 2.
    assert rooms['S90003'] == c.aula
    assert incumbents and any(r[a.id] == r[b.id] for r, _ in incumbents)


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


def test_inherited_fixed_room_overlap_is_allowed():
    from nivell2.base import avalua_rapid
    a, b = session('S90001', room='Q9/0001'), session('S90002', room='Q9/0001')
    a.fixada = b.fixada = 'R1: fixed'
    data = base(a, b)
    assert avalua_rapid(data, Proposta.de_base(data), nomes_aules=True).veredicte == 'VALIDA'
    rooms, status = solve(data)
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert rooms[a.id] == rooms[b.id] == 'Q9/0001'


def test_new_overlap_with_fixed_room_is_forbidden():
    a, b = session('S90001', room='Q9/0001'), session('S90002', room='Q9/0002', day=9)
    a.fixada = b.fixada = 'R1: fixed'
    data = base(a, b)
    assert assigna_aules(data, {s.id: (a.data, a.ini) for s in (a, b)}, temps_s=2)[0] == {
        a.id: 'Q9/0001', b.id: 'Q9/0002'}
    b.aula = a.aula
    assert assigna_aules(data, {s.id: (a.data, a.ini) for s in (a, b)}, temps_s=2)[1] == 'INFEASIBLE'


def test_recovered_capacity_uses_model_estimates_and_shared_sum():
    from copy import deepcopy
    from nivell2.s51 import aforament_model_ok
    official = base(session('S90001', students=0, room='Q9/0001'))
    model = deepcopy(official)
    model.sessions['S90001'].alumnes = 50
    p = Proposta.de_base(official)
    assert aforament_model_ok(official, p)
    assert not aforament_model_ok(model, p)
    p.files['S90001'].aula = 'Q9/0002'
    assert aforament_model_ok(model, p)
    shared = base(session('S90001', shared='C90001', students=20, room='Q9/0001'),
                  session('S90002', shared='C90001', students=20, room='Q9/0001'),
                  session('S90003', shared='C90001', students=100, sense_espai=True))
    assert not aforament_model_ok(shared, Proposta.de_base(shared))
    for row in shared.sessions.values():
        row.aula = 'Q9/0002'
    assert aforament_model_ok(shared, Proposta.de_base(shared))


def test_recovered_capacity_keeps_only_unchanged_fixed_exemption():
    from nivell2.s51 import aforament_model_ok
    a = session('S90001', students=70, room='Q9/0001')
    a.fixada = 'R1: fixed'
    data = base(a)
    p = Proposta.de_base(data)
    assert aforament_model_ok(data, p)
    p.files[a.id].aula = 'Q9/0002'
    assert not aforament_model_ok(data, p)


def test_extra_rooms_reports_official_and_without_doubles():
    from nivell2.base import avalua_rapid
    from nivell2.s51 import comparacio_extres
    a, b = session('S90001', room='Q9/0001'), session('S90002', room='Q9/0002', sense_espai=True)
    a.cohorts = b.cohorts = ('GXX:1r',)
    data = base(a, b)
    p = Proposta.de_base(data)
    assert avalua_rapid(data, p, nomes_aules=True).objectius['r6_aules_te_extra_per_grup'] == 1
    assert comparacio_extres(data, p) == {'r6_aules_te_extra_sense_dobles': (0, 0)}


def test_csv_normalizes_case_spaces_and_rejects_duplicates(tmp_path):
    import pytest
    from nivell2.s51 import llegeix_proposta
    path = tmp_path / 'inventada.csv'
    path.write_text(' id_sessio , Dia , h_ini , aula \n s90001 , m , 08:30 , q9/0001 \n')
    p = llegeix_proposta(path)
    assert p.files['S90001'].dia == 'M' and p.files['S90001'].aula == 'Q9/0001'
    with path.open('a') as f:
        f.write('S90001,M,08:30,Q9/0001\n')
    with pytest.raises(ValueError, match='duplicats'):
        llegeix_proposta(path)


def test_solver_and_selector_share_quality_and_weights():
    from nivell2.aules import qualitat_aules, PES_CANVI, PES_PASSADIS
    from nivell2.s51 import qualitat
    a, b = session('S90001', room='Q9/0001'), session('S90002', room='Q9/1001', start=570)
    a.cohorts = b.cohorts = ('GXX:1r',)
    b.tipus, b.grup = 'PAUL', 'PAUL/811'
    data = base(a, b)
    data.aules['Q9/1001'] = Aula('Q9/1001', 'Q9', 'Aules docents', 30)
    p = Proposta.de_base(data)
    assert qualitat(data, p) == (0, 0, PES_PASSADIS)
    p.files[b.id].aula = a.aula
    assert qualitat(data, p) == (0, 0, PES_CANVI)
    rooms, _ = solve(data)
    assert qualitat_aules(data, rooms) == (0, 0, PES_PASSADIS)


def test_theory_unions_also_try_unmerged_after_feasible(monkeypatch):
    from ortools.sat.python import cp_model
    calls = []
    original = cp_model.CpSolver.solve
    def track(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(cp_model.CpSolver, 'solve', track)
    a, b = session('S90001'), session('S90002', start=570)
    a.cohorts = b.cohorts = ('GXX:1r',)
    assert solve(base(a, b), agrupa_te=True)[0]
    assert len(calls) == 2


def test_reference_restoration_keeps_shared_activity_block_and_skips_doubles():
    from nivell2.s51 import restauracions_referencia
    data = base(session('S90001', activity='A9001', shared='C90001', room='Q9/0001'),
                session('S90002', activity='A9002', shared='C90001', room='Q9/0001'),
                session('S90003', activity='A9001', day=9, room='Q9/0001'),
                session('S90004', activity='A9002', day=9, start=570, room='Q9/0001'),
                session('S90005', activity='A9001', sense_espai=True))
    assert list(restauracions_referencia(data)) == [(
        {'S90001', 'S90002', 'S90003', 'S90004'}, 'Q9/0001')]


def test_inherited_shared_room_conflicts_use_physical_units():
    rows = [session(f'S9000{i}', shared=unit, room='Q9/0003')
            for i, unit in enumerate(('C90001', 'C90001', 'C90002', 'C90002'), 1)]
    for row in rows:
        row.fixada = 'R1: fixed'
    rooms, status = solve(base(*rows))
    assert status in ('OPTIMAL', 'FEASIBLE')
    assert set(rooms.values()) == {'Q9/0003'}


if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main([__file__, '-q']))

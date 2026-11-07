"""Proves locals; la prova real només s'activa amb pytest -m complet."""
import datetime as dt
import sys

import unittest

try:
    import pytest
except ImportError:
    pytest = None

from nivell2.base import Base, Proposta, Sessio, carrega_model, carrega_oficial, avalua_rapid
from horaris.model import Aula
from nivell2.franges import assigna_franges, proposta_franges


def sessio(sid, **kw):
    args = dict(id=sid, codi=sid, tipus='TE', grup='TE/81',
                data=dt.date(2027, 2, 8), dia='L', ini=540, durada=60,
                alumnes=20, aula='', cohorts=('GED:3r',), torn='tarda',
                fixada='', docents=frozenset({'D1'}), activitat=sid)
    args.update(kw)
    return Sessio(**args)


def base_petita(*rows, **kw):
    rooms = {str(i): Aula(str(i), 'Q', 'Aules docents', 100) for i in range(6)}
    return Base({s.id: s for s in rows}, rooms, [s.id for s in rows], **kw)


def resol(b, **kw):
    r, state, notes = assigna_franges(b, referencia=Proposta.de_base(b), temps_s=5, **kw)
    assert state in ('OPTIMAL', 'FEASIBLE')
    inf = avalua_rapid(b, proposta_franges(b, Proposta.de_base(b), r))
    forbidden = {'R1-TORN', 'R2-FINESTRA', 'R2-CALENDARI', 'R4-DOCENT', 'R4-ALUMNAT', 'R4-PLAB', 'R4-COMPARTIDA'}
    assert not [v for v in inf.violacions if v.compta and v.regla in forbidden]
    return r, notes


def test_torn_rutina_i_fixada():
    a = sessio('a', activitat='A')
    b = sessio('b', activitat='A', data=a.data+dt.timedelta(days=7))
    lab = sessio('lab', tipus='PLAB', fixada='R7', ini=870, codi='a')
    base = base_petita(a, b, lab)
    r, notes = resol(base)
    assert r['lab'] == (lab.data, lab.ini)
    assert r['a'][0].weekday() == r['b'][0].weekday()
    assert r['a'][1] == r['b'][1] >= 930
    assert not notes


def test_compartides_i_heretats():
    a = sessio('a', compartida='shared')
    b = sessio('b', compartida='shared', cohorts=('GEQ:3r',))
    c = sessio('c')  # conflicte de partida admès
    r, _ = resol(base_petita(a, b, c))
    assert r['a'] == r['b']


def test_calendari_excepcio():
    a = sessio('a', activitat='A', ini=870)
    b = sessio('b', activitat='A', ini=540, dia='M', data=a.data+dt.timedelta(days=8))
    # Forcem el primer dilluns; el segon dilluns és festiu.
    base = base_petita(a, b, dies_sense_classe=frozenset({b.data-dt.timedelta(days=1)}), aturades={b.data-dt.timedelta(days=1): [(0,1440)]})
    r, notes = resol(base, fixes={'a': (a.data, 870)})
    assert r['b'][0].weekday() != 0
    assert notes and 'calendari' in notes[0]['motiu']


def test_quarts_i_dades_invalides():
    a = sessio('a', ini=885)
    r, _ = resol(base_petita(a))
    assert r['a'][1] == 885
    with unittest.TestCase().assertRaises(ValueError):
        assigna_franges(base_petita(a), referencia=Proposta.de_base(base_petita(a)), fixes={'absent': (a.data, 870)})


def test_sense_solucio():
    a = sessio('a', durada=500)
    assert assigna_franges(base_petita(a), referencia=Proposta.de_base(base_petita(a)))[1] == 'INFEASIBLE'


# Registre local: no cal editar la configuració compartida de pytest.
if pytest is not None and pytest.mark._config is not None:
    pytest.mark._config.addinivalue_line('markers', 'complet: resol el semestre real')



def test_solapament_nou_i_capacitat_horaria():
    a = sessio('a', ini=540)
    b = sessio('b', ini=660)
    r, _ = resol(base_petita(a, b))
    if r['a'][0] == r['b'][0]:
        assert abs(r['a'][1] - r['b'][1]) >= 60
    # Tres aules menys dues de reserva: una aula ocupada per cubell horari.
    # Dues mitges hores consecutives toquen el mateix cubell 14:30-15:30.
    a = sessio('a', ini=870, durada=30, docents=frozenset(), cohorts=('A:3r',))
    b = sessio('b', ini=990, durada=30, docents=frozenset(), cohorts=('B:3r',))
    base = base_petita(a, b)
    base.aules = dict(list(base.aules.items())[:3])
    ref = Proposta.de_base(base)
    r, state, _ = assigna_franges(base, referencia=ref, temps_s=3,
                                 fixes={'a': (a.data, 870), 'b': (b.data, 900)})
    assert state == 'FEASIBLE'
    assert r['a'] == (a.data,870) and r['b'] == (b.data,900)
    # The final room model must permit reuse within the hour as well.
    from nivell2.aules import assigna_aules
    rooms, state = assigna_aules(base,r,temps_s=3)
    assert state in ('OPTIMAL','FEASIBLE')
    assert rooms['a'] == rooms['b']
    proposal = proposta_franges(base,ref,r)
    for sid,room in rooms.items():
        proposal.files[sid].aula = room
    assert not [v for v in avalua_rapid(base,proposal).violacions if v.compta and v.regla == 'R8-RESERVA']


def test_hores_mortes_heretades():
    from ortools.sat.python import cp_model
    from nivell2.franges import _hores_mortes, _setmana
    # L'interval llarg heretat no ha d'amagar el buit després del curt:
    # el verificador ordena per inici i compara parells consecutius.
    rows = [sessio('a', ini=870, durada=180), sessio('b', ini=900, durada=30),
            sessio('c', ini=990, durada=30)]
    base = base_petita(*rows)
    m = cp_model.CpModel()
    units = {s.id: [s] for s in rows}
    starts = {s.id: m.new_constant(s.ini) for s in rows}
    costs = _hores_mortes(m, base, units, starts, {_setmana(rows[0]): list(units)})
    solver = cp_model.CpSolver()
    assert solver.solve(m) == cp_model.OPTIMAL
    assert sum(solver.value(c) for c in costs) == 60


def test_capacitat_obstacles_amb_certificat():
    a = sessio('a', ini=870, fixada='R1', cohorts=('A:3r',), docents=frozenset())
    b = sessio('b', ini=870, fixada='R1', cohorts=('B:3r',), docents=frozenset())
    base = base_petita(a,b)
    base.aules = dict(list(base.aules.items())[:3])
    r,state,notes = assigna_franges(base,referencia=Proposta.de_base(base),temps_s=2)
    assert not r and state == 'INFEASIBLE'
    assert notes[0]['demanda'] == 2 and notes[0]['oferta'] == 1
    assert notes[0]['h_ini'] == '14:30'


def test_activitats_correctes_congelades():
    a = sessio('a',ini=870,activitat='correcta')
    b = sessio('b',ini=540,activitat='moure')
    base = base_petita(a,b)
    r,_ = resol(base)
    assert r['a'] == (a.data,a.ini)
    assert r['b'][1] >= 870


def test_cost_canvi_es_per_sessio_i_optimitza_hores_mortes():
    import time
    from nivell2.franges import _problema, _resol_torn
    from horaris.model import TARDA
    # Fifteen dates share a variable with one singleton activity. They start
    # at different times in the reference; preserving fifteen dates must win.
    rows = [sessio(f'inventat-a{i}',activitat='A',ini=900,
                   data=dt.date(2027,2,8)+dt.timedelta(weeks=i),
                   cohorts=(),docents=frozenset()) for i in range(15)]
    singleton = sessio('inventat-b',activitat='B',ini=960,cohorts=(),docents=frozenset())
    base = base_petita(*rows,singleton)
    ref = Proposta.de_base(base)
    units,weeks,edges,groups = _problema(base,ref,{})
    # This synthetic shared component has one common decision across dates.
    groups = {u:'component' for u in units}
    current = {r.id:(r.data,r.ini) for r in base.sessions.values()}
    result,state = _resol_torn(base,units,weeks,edges,groups,{'component'},current,
                              ref,{},TARDA,time.monotonic()+5,0)
    assert state == 'OPTIMAL'
    assert all(result[r.id][1] == 900 for r in rows)
    assert result[singleton.id][1] == 900
    # With a mandatory move, the gap term selects the adjacent slot.
    fixed = sessio('inventat-fix',ini=870,fixada='R1',durada=60)
    moved = sessio('inventat-mou',ini=540)
    result,_ = resol(base_petita(fixed,moved))
    assert result[moved.id] == (fixed.data,930)


class TestFranges(unittest.TestCase):
    pass


# unittest també permet validar sense instal·lar res a l’entorn del repte.
for _name, _fn in list(globals().items()):
    if _name.startswith("test_"):
        setattr(TestFranges, _name, staticmethod(_fn))
        del globals()[_name]

del _name, _fn

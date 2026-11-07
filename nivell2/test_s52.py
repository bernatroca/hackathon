"""Proves ràpides de la integració sense resoldre el semestre complet."""
from unittest.mock import patch
from nivell2.base import Proposta
from nivell2.test_franges import base_petita, sessio
from nivell2.s52 import resol, escriu_csv


def test_integra_referencia_i_aules():
    s = sessio('a', ini=870)
    b = base_petita(s)
    slots = {'a': (s.data, 930)}
    with patch('nivell2.s52.assigna_franges',return_value=(slots,'FEASIBLE',[])) as f, \
         patch('nivell2.s52.assigna_aules',return_value=({'a':'0'},'OPTIMAL')) as a:
        f.estadistiques = {}
        p,ex,h = resol(b,temps_franges=1,temps_aules=1)
    assert p.files['a'].h_ini == '15:30'
    assert p.files['a'].aula == '0'
    assert a.call_args.kwargs['referencia'] == Proposta.de_base(b)
    assert h[0]['franges'] == 'FEASIBLE' and h[0]['aules'] == 'OPTIMAL'


def test_reintent_limitat_sense_relaxacio():
    s = sessio('a',ini=870)
    b = base_petita(s)
    with patch('nivell2.s52.assigna_franges',return_value=({'a':(s.data,s.ini)},'FEASIBLE',[])) as f, \
         patch('nivell2.s52.assigna_aules',return_value=({},'INFEASIBLE')) as a:
        f.estadistiques = {}
        p,_,history = resol(b,temps_franges=10,temps_aules=10)
    assert p is None and len(history) == 3 and a.call_count == 3
    assert history[1]['limits_capacitat'][-1] == 3
    assert history[2]['limits_capacitat'][-1] == 2


def test_unknown_franges_no_crida_aules():
    with patch('nivell2.s52.assigna_franges',return_value=({},'UNKNOWN',[])) as f, \
         patch('nivell2.s52.assigna_aules') as a:
        f.estadistiques = {}
        p,_,h = resol(base_petita(sessio('a')))
    assert p is None and not a.called and h[0]['franges'] == 'UNKNOWN'


def test_excepcions_buides_amb_capcalera(tmp_path):
    path = tmp_path/'excepcions.csv'
    escriu_csv(path,[],['id_sessio','motiu'])
    assert path.read_text().strip() == 'id_sessio,motiu'


def test_model_setmana_excepcions_minimes_i_originals():
    import datetime as dt
    import time
    from nivell2.franges import _problema, _resol_torn
    from horaris.model import MATI, TARDA
    date = dt.date(2027,4,9)
    a = sessio('a',data=date,dia='V',ini=540)
    b = sessio('b',data=date,dia='V',ini=660)
    lab = sessio('lab',data=date,dia='V',ini=870,durada=390,tipus='PLAB',fixada='R7')
    base = base_petita(a,b,lab,dies_sense_classe=frozenset(date-dt.timedelta(days=d) for d in range(1,5)))
    ref = Proposta.de_base(base)
    units,weeks,edges,groups = _problema(base,ref,{})
    current = {s.id:(s.data,s.ini) for s in base.sessions.values()}
    common = dict(reparacio=True,setmana_completa=True)
    result,state = _resol_torn(base,units,weeks,edges,groups,set(units),current,ref,{},
        (MATI[0],TARDA[1]),time.monotonic()+5,0,**common)
    assert result is None and state == 'INFEASIBLE'
    result,state = _resol_torn(base,units,weeks,edges,groups,set(units),current,ref,{},
        (MATI[0],TARDA[1]),time.monotonic()+5,0,torn_tou=True,**common)
    assert state == 'OPTIMAL'
    assert result == current  # Les dues excepcions només poden conservar la partida.


def test_rebutja_relaxacio_fora_w14_i_fora_original():
    import datetime as dt
    import pytest
    from nivell2.s52 import valida_excepcions
    a = sessio('a')
    b = base_petita(a)
    with pytest.raises(ValueError):
        valida_excepcions(b,Proposta.de_base(b),['a'])
    a.data = dt.date(2027,4,9)
    a.dia = 'V'
    p = Proposta.de_base(b)
    valida_excepcions(b,p,['a'])
    p.files['a'].h_ini = '10:00'
    with pytest.raises(ValueError):
        valida_excepcions(b,p,['a'])

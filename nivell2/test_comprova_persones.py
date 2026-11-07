"""Proves amb dades inventades de nivell2/comprova_persones.py."""
import datetime as dt

from nivell2.base import Base, Proposta, Sessio
from horaris.check import Informe, _col_loca
from horaris.model import Aula
from nivell2.comprova_persones import comprova_dobles, conflictes, parelles_dobles

DIA = dt.date(2027, 2, 8)


def sessio(sid, **kw):
    args = dict(id=sid, codi='900001', tipus='TE', grup='TE/91', data=DIA, dia='L', ini=900, durada=60,
                alumnes=20, aula='A', cohorts=('GXX:3r',), torn='tarda', fixada='',
                docents=frozenset({'D' + sid}), activitat=sid)
    args.update(kw)
    return Sessio(**args)


def base(*ss):
    aules = {n: Aula(n, 'Q', 'Aules docents', 60) for n in ('A', 'B', 'C')}
    return Base({s.id: s for s in ss}, aules, [s.id for s in ss])


def col(b, canvis=None):
    p = Proposta.de_base(b)
    for sid, (ini, aula) in (canvis or {}).items():
        p.files[sid].h_ini, p.files[sid].aula = ini, aula
    return _col_loca(b, p.a_files(), Informe())


def test_dues_classes_alhora_del_mateix_estudi():
    b = base(sessio('1'), sessio('2', codi='900002', grup='TE/91', aula='B', ini=930))
    assert list(conflictes(col(b)).values()) == ['diferents']


def test_estudis_diferents_o_subgrups_diferents_no_es_trepitgen():
    b = base(sessio('1'), sessio('2', codi='900002', cohorts=('GYY:3r',), aula='B'),
             sessio('3', codi='900003', tipus='PAUL', grup='PAUL/911', aula='C', ini=1020),
             sessio('4', codi='900004', tipus='PAUL', grup='PAUL/912', aula='A', ini=1020))
    assert conflictes(col(b)) == {}


def test_una_proposta_que_crea_un_solapament_es_detecta_com_a_nou():
    b = base(sessio('1'), sessio('2', codi='900002', aula='B', ini=1020))
    assert conflictes(col(b)) == {}
    assert conflictes(col(b, {'2': ('15:00', 'B')})) == {('1', '2'): 'diferents'}


def test_classe_repetida_de_la_mateixa_assignatura():
    b = base(sessio('1'), sessio('2', aula='B', ini=1020))
    assert conflictes(col(b, {'2': ('15:00', 'B')})) == {('1', '2'): 'repetida'}


def test_doble_va_amb_la_classe_d_un_altre_grup():
    grau = sessio('1')
    doble = sessio('2', aula='', cohorts=('GDD:4t',), sense_espai=True, docents=frozenset({'D1'}))
    b = base(grau, doble)
    parelles, sense = parelles_dobles(b)
    assert parelles == {'2': ['1']} and sense == 0
    assert comprova_dobles(b, col(b), parelles) == {'separades': [], 'duplicades': []}
    # Moure la classe del grau i no la del doble les separa.
    assert comprova_dobles(b, col(b, {'1': ('17:00', 'A')}), parelles)['separades'] == ['2']
    # Donar aula pròpia diferent al doble duplica la classe; la mateixa aula no.
    assert comprova_dobles(b, col(b, {'2': ('15:00', 'B')}), parelles)['duplicades'] == ['2']
    assert comprova_dobles(b, col(b, {'2': ('15:00', 'A')}), parelles)['duplicades'] == []


def test_doble_sense_classe_a_la_mateixa_hora():
    b = base(sessio('1'), sessio('2', aula='', ini=1020, sense_espai=True, cohorts=('GDD:4t',)))
    assert parelles_dobles(b) == ({}, 1)

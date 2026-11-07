"""Proves amb dades inventades de nivell2/comprova_persones.py."""
import datetime as dt
import pytest

from nivell2.base import Base, Proposta, Sessio
from horaris.check import Informe, _col_loca
from horaris.model import Aula
from nivell2.comprova_persones import (comprova_dobles, conflictes, conflictes_docents,
                                      diagnosi_dobles, parelles_dobles)
from nivell2.alumnat import ReglaAlumnat

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
    b = base(sessio('1', alumnes=40), sessio('2', codi='900002', cohorts=('GYY:3r',), aula='B'),
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


def test_doble_amb_grup_propi_s_aparella_per_assignatura_dia_i_hora():
    b = base(sessio('1', grup='TE/91'), sessio('2', grup='TE/51', aula='', cohorts=('GDD:4t',), sense_espai=True))
    parelles, sense = parelles_dobles(b)
    assert parelles == {'2': ['1']} and sense == 0
    d = diagnosi_dobles(b)
    assert d['assignatura, tipus, grup, dia i hora'] == 0
    assert d['assignatura, tipus, dia i hora'] == 1
    assert d['de tipus TE'] == 1 and d['tenen aula avui'] == 0


def test_doble_sense_classe_a_la_mateixa_hora():
    b = base(sessio('1'), sessio('2', aula='', ini=1020, sense_espai=True, cohorts=('GDD:4t',)))
    assert parelles_dobles(b) == ({}, 1)


def test_te91_cobreix_paul92_de_la_mateixa_cohort():
    te = sessio('1', alumnes=40)
    paul = sessio('2', tipus='PAUL', grup='PAUL/92', alumnes=20, codi='900002', aula='B')
    b = base(te, paul)
    assert ReglaAlumnat(b.sessions.values())(te, paul)
    assert conflictes(col(b)) == {('1', '2'): 'diferents'}


def test_cohort_completa_per_mida_amb_mes_d_una_teoria():
    a = sessio('1', grup='TE/91')
    b = sessio('2', grup='TE/92')
    completa = sessio('3', tipus='SEM', grup='SEM/5', alumnes=40)
    regla = ReglaAlumnat([a, b, completa], mides={'GXX:3r': 40})
    assert regla(completa, b)
    assert not regla(a, b)
    assert not regla(completa, sessio('4', cohorts=('ALTRE:3r',)))


def test_te_unica_sense_aforament_i_subgrups_ambigus():
    te = sessio('1', alumnes=0)
    a = sessio('2', tipus='PAUL', grup='PAUL/911', alumnes=20)
    b = sessio('3', tipus='PAUL', grup='PAUL/912', alumnes=20)
    regla = ReglaAlumnat([te, a, b])
    assert regla(te, b)
    assert regla(a, b)  # Sense mida no podem justificar que siguin disjunts.
    te.alumnes = 40
    regla = ReglaAlumnat([te, a, b])
    assert not regla(a, b)
    assert regla(a, sessio('4', tipus='SEM', grup='SEM/912'))
    assert regla(a, sessio('5', tipus='PAUL', grup='PAUL/92'))


def test_docents_comuns_entre_cohorts_i_deduplicats():
    a = sessio('1', docents=frozenset({'D1', 'D2'}))
    b = sessio('2', cohorts=('ALTRE:3r',), docents=a.docents, ini=1020)
    bb = base(a, b)
    before = conflictes_docents(col(bb))
    after = conflictes_docents(col(bb, {'2': ('15:30', 'B')}))
    assert before == {}
    assert after == {('1', '2'): 'docent'}
    assert set(after) - set(before) == {('1', '2')}
    assert conflictes(col(bb, {'2': ('15:30', 'B')})) == {}
    assert conflictes_docents(col(bb, {'2': ('16:00', 'B')})) == {}


def test_docents_exclouen_la_mateixa_unitat_compartida():
    a = sessio('1', compartida='inventada', docents=frozenset({'D1'}))
    b = sessio('2', compartida='inventada', docents=a.docents, cohorts=('ALTRE:3r',))
    assert conflictes_docents(col(base(a, b))) == {}


@pytest.mark.parametrize('heretat', [False, True])
def test_comprovacio_separa_docents_nous_dels_heretats(monkeypatch, tmp_path, capsys, heretat):
    import nivell2.comprova_persones as persones
    import nivell2.junta as junta
    a = sessio('1', docents=frozenset({'D-inventat'}))
    b = sessio('2', ini=900 if heretat else 1020, docents=a.docents, cohorts=('ALTRE:3r',))
    bb = base(a, b)
    after = col(bb, {'2': ('15:30', 'B')})
    monkeypatch.setattr(persones, 'escenaris', lambda *_: [('inventat', tmp_path/'proposta.csv', None)])
    monkeypatch.setattr(persones, 'carrega_oficial', lambda *_: bb)
    monkeypatch.setattr(junta, 'carrega_proposta', lambda *_: (None, after))
    assert persones.comprova() == heretat
    assert f'nous respecte d’avui: {0 if heretat else 1}' in capsys.readouterr().out

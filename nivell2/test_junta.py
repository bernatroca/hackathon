"""Regressions réelles i casos amb demanda i canvis coneguts."""
import json
from copy import deepcopy
from datetime import date, timedelta
from functools import lru_cache

import pytest

from nivell2.base import Base, PAQUET, Proposta, Sessio, carrega_model, carrega_oficial
from nivell2.junta import calcula, carrega_proposta, documents, main, pics_i_mides
from horaris.check import Informe, _col_loca
from horaris.model import Aula


@lru_cache(maxsize=1)
def reals():
    b, m = carrega_oficial(), carrega_model()
    p, col = carrega_proposta(PAQUET / 'proposta_partida.csv', b)
    return b, m, p, col


def petita():
    sessions = {}
    for i in range(3):
        s = Sessio(str(i), '1', 'TE', '81', date(2027, 2, 1) + timedelta(weeks=i),
                   'L', 510, 60, 40, 'A', ('GED:1r',), 'mati', '', frozenset())
        sessions[s.id] = s
    return Base(sessions, {'A': Aula('A', '', 'Aules docents', 50)}, list(sessions))


def colloca(b, p):
    return _col_loca(b, p.a_files(), Informe())


def test_pic_15_de_19():
    b, m, _, col = reals()
    r = pics_i_mides(b, m, col, nomes_mati_requerit=True)
    assert r['mati']['pitjor']['classes'] == 15
    assert r['mati']['pitjor']['aules_disponibles'] == 19


def test_partida_i_excepcions_completes():
    b, m, p, col = reals()
    d = calcula(p, b, m, col)
    assert all(r['mogudes_pct'] == 0 for r in d['sessions_mogudes'])
    esperades = [sid for sid, c in col.items() if c.s.torn in ('mati', 'tarda')
                 and (c.ini < 870) != (c.s.torn == 'mati')]
    assert {e['id_sessio'] for e in d['excepcions']} == set(esperades)
    assert all(e['motiu'] == "No s'ha explicat per què" and e['prova'] for e in d['excepcions'])
    assert sum(r['sessions'] for r in d['excepcions_resum']) >= len(esperades)


def test_percentatges_unio_i_pitjor_cohort(tmp_path):
    b = petita()
    s = deepcopy(b.sessions['0'])
    s.id, s.cohorts = 'extra', ('GEQ:1r',)
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    p.files['0'].h_ini, p.files['0'].aula = '15:00', 'B'
    p.files['extra'].aula = 'B'
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,0,Prova explicada\n')
    d = calcula(p, b, b, colloca(b, p), relax)
    rows = {r['cohort']: r for r in d['sessions_mogudes']}
    assert rows['GED:1r']['mogudes'] == 1
    assert rows['GED:1r']['mogudes_pct'] == pytest.approx(100 / 3)
    assert rows['GEQ:1r']['mogudes_pct'] == 0
    assert rows['GEQ:1r']['aula'] == 1
    assert d['pitjor_cohort'] == ['GED:1r']
    assert d['excepcions'][0]['motiu'] == 'Prova explicada'
    assert d['excepcions_resum'][0]['percentatge'] == pytest.approx(100 / 3)


def test_compartida_suma_alumnes_i_no_duplica_classes():
    b = petita()
    s = deepcopy(b.sessions['0'])
    s.id, s.cohorts, s.alumnes = 'extra', ('GEQ:1r',), 30
    s.compartida = b.sessions['0'].compartida = 'compartida'
    s.aula = b.sessions['0'].aula = ''
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['pitjor']['classes'] == 1
    assert r['mides'][3]['demanda_acumulada'] == 1
    assert r['mides'][3]['falten'] == 1


def test_tipica_mediana_i_franja_interseccio():
    b = petita()
    s = deepcopy(b.sessions['0'])
    s.id, s.ini, s.durada = 'extra', 555, 30
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['pitjor']['classes'] == 1
    assert r['tipica']['classes'] == 1
    assert r['tipica']['setmana'] == '2027-W06'


def test_sense_excepcions_i_html_segura():
    b = petita()
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    md, html = documents(d)
    assert 'No hi ha cap sessió fora del torn requerit.' in md
    assert '@page{size:A4' in html and '@media print' in html
    d['excepcions'] = [{}]
    d['excepcions_resum'] = [{'motiu': '<script>alert(1)</script>', 'nom': 'Grup',
                             'percentatge': 1, 'sessions': 1}]
    assert '<script>alert(1)</script>' not in documents(d)[1]
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in documents(d)[1]


def test_rebutja_duplicades_i_absents(tmp_path):
    b = petita()
    p = Proposta.de_base(b)
    path = p.escriu(tmp_path / 'p.csv')
    path.write_text(path.read_text() + '0,L,08:30,A\n')
    with pytest.raises(ValueError, match='format incorrecte'):
        carrega_proposta(path, b)
    del p.files['0']
    p.escriu(path)
    with pytest.raises(ValueError, match='incompleta'):
        carrega_proposta(path, b)


def test_cli_tres_fitxers(tmp_path):
    assert main([str(PAQUET / 'proposta_partida.csv'), '--sortida', str(tmp_path)]) == 0
    d = json.loads((tmp_path / 'junta.json').read_text())
    assert {'pics', 'sessions_mogudes', 'excepcions', 'excepcions_resum'} <= d.keys()
    assert all((tmp_path / f'junta.{ext}').stat().st_size for ext in ('json', 'md', 'html'))


def test_proposta_51_pic_i_franja():
    from pathlib import Path
    path = Path('/Users/bernatroca/Bernat/Hackathon/resultats/nivell2/5.1/proposta.csv')
    b, m, _, _ = reals()
    p, col = carrega_proposta(path, b)
    d = calcula(p, b, m, col)
    assert all(r['mogudes_pct'] == 0 for r in d['sessions_mogudes'])
    assert all(d['pics'][t]['pitjor']['classes'] <= 19 for t in ('mati', 'tarda'))
    assert all(not d['pics'][t]['pitjor']['estimacio'] for t in ('mati', 'tarda'))


def test_assignar_aula_no_es_moure():
    b = petita()
    b.sessions['0'].aula = ''
    b.sessions['1'].aula = 'J/001'
    b.sessions['2'].sense_espai = True
    p = Proposta.de_base(b)
    for a in p.files.values():
        a.aula = 'A'
    d = calcula(p, b, b, colloca(b, p))
    r, = d['sessions_mogudes']
    assert r['mogudes'] == r['aula'] == 0
    assert r['aules_assignades'] == 1


def test_pic_exclou_seminaris_i_externes_i_compta_aules_diferents():
    b = petita()
    b.aules['S'] = Aula('S', '', 'Seminaris', 30)
    for i, aula in enumerate(('S', 'B3/0021', '')):
        s = deepcopy(b.sessions['0'])
        s.id, s.aula = f'extra{i}', aula
        b.sessions[s.id] = s
        b.ordre.append(s.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']['pitjor']
    assert r['classes'] == 2 and r['estimacio']


def test_proposta_51_mides_coincideixen_amb_pic():
    from pathlib import Path
    path = Path('/Users/bernatroca/Bernat/Hackathon/resultats/nivell2/5.1/proposta.csv')
    b, m, _, _ = reals()
    _, col = carrega_proposta(path, b)
    for torn in pics_i_mides(b, m, col).values():
        assert torn['total_mides'] == torn['pitjor']['classes']
        assert sum(r['ocupades_al_pic'] for r in torn['mides']) == torn['pitjor']['classes']
        assert torn['mides'][0]['demanda_acumulada'] == torn['pitjor']['classes']
        assert all(r['marge'] >= 0 and r['falten'] == 0 for r in torn['mides'])
        assert all(r['pic_categoria'] <= r['aules_categoria'] for r in torn['mides'])


def test_mides_aula_assignada_i_classes_successives():
    b = petita()
    b.aules['A'] = Aula('A', '', 'Aules docents', 90)
    b.aules['S'] = Aula('S', '', 'Seminaris', 30)
    for i, (aula, ini, durada) in enumerate((('A', 540, 30), ('S', 510, 60))):
        sessio = deepcopy(b.sessions['0'])
        sessio.id, sessio.aula = f'extra{i}', aula
        sessio.ini, sessio.durada = ini, durada
        b.sessions[sessio.id] = sessio
        b.ordre.append(sessio.id)
    b.sessions['0'].durada = 30
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['pitjor']['classes'] == r['total_mides'] == 1
    assert not r['pitjor']['estimacio']
    assert r['mides'][3]['pic_categoria'] == 1
    assert r['mides'][1]['pic_categoria'] == 0
    assert all(m['marge'] >= 0 for m in r['mides'])


def test_estimacio_mides_mateix_filtre_que_pic():
    b = petita()
    b.sessions['0'].aula = ''
    b.aules['S'] = Aula('S', '', 'Seminaris', 30)
    for i, aula in enumerate(('S', 'B3/0021')):
        sessio = deepcopy(b.sessions['0'])
        sessio.id, sessio.aula = f'extra{i}', aula
        b.sessions[sessio.id] = sessio
        b.ordre.append(sessio.id)
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    r = d['pics']['mati']
    assert r['pitjor']['estimacio']
    assert r['mides'][0]['demanda_acumulada'] == r['total_mides'] == 1
    assert r['mides'][1]['pic_categoria'] == 1
    md, html = documents(d)
    assert 'Matí (estimació)' in md and 'Matí (estimació)' in html

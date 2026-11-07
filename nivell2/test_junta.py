"""Casos inventats amb demanda i canvis coneguts."""
import json
from copy import deepcopy
from datetime import date, timedelta

import pytest

from nivell2.base import Base, CONTINGENCIES, GRAU_NOU, Proposta, Sessio
from nivell2.junta import (RESERVA, aulari, calcula, carrega_proposta, documents,
                          escenari_proposta, main, pics_i_mides)
from horaris.check import Informe, _col_loca
from horaris.model import Aula


def petita():
    sessions = {}
    for i in range(3):
        s = Sessio(str(i), '1', 'TE', '81', date(2027, 2, 1) + timedelta(weeks=i),
                   'L', 510, 60, 40, 'A', ('GXX:1r',), 'mati', '', frozenset())
        sessions[s.id] = s
    aules = {'A': Aula('A', '', 'Aules docents', 50)}
    aules.update({f'Reserva{i}': Aula(f'Reserva{i}', '', 'Aules docents', 30)
                  for i in range(RESERVA)})
    return Base(sessions, aules, list(sessions))


def colloca(b, p):
    return _col_loca(b, p.a_files(), Informe())


def test_percentatges_unio_i_pitjor_cohort(tmp_path):
    b = petita()
    s = deepcopy(b.sessions['0'])
    s.id, s.cohorts = 'extra', ('GYY:1r',)
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    p.files['0'].h_ini, p.files['0'].aula = '15:00', 'B'
    p.files['extra'].aula = 'B'
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,0,Prova explicada\n')
    d = calcula(p, b, b, colloca(b, p), relax)
    rows = {r['cohort']: r for r in d['sessions_mogudes']}
    assert rows['GXX:1r']['mogudes'] == 1
    assert rows['GXX:1r']['mogudes_pct'] == pytest.approx(100 / 3)
    assert rows['GYY:1r']['mogudes_pct'] == 0
    assert rows['GYY:1r']['aula'] == 1
    assert d['pitjor_cohort'] == ['GYY:1r']
    assert d['excepcions'][0]['motiu'] == 'Prova explicada'
    assert d['excepcions_resum'][0]['percentatge'] == pytest.approx(100 / 3)


def test_compartida_suma_alumnes_i_no_duplica_classes():
    b = petita()
    s = deepcopy(b.sessions['0'])
    s.id, s.cohorts, s.alumnes = 'extra', ('GYY:1r',), 30
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
    assert 'No hi ha excepcions noves als torns.' in md
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


def test_cli_tres_fitxers(tmp_path, monkeypatch):
    b = petita()
    monkeypatch.setattr('nivell2.junta.carrega_oficial', lambda escenari=None: b)
    monkeypatch.setattr('nivell2.junta.carrega_model', lambda escenari=None: b)
    proposta = Proposta.de_base(b).escriu(tmp_path / 'inventada.csv')
    assert main([str(proposta), '--sortida', str(tmp_path)]) == 0
    d = json.loads((tmp_path / 'junta.json').read_text())
    assert {'pics', 'sessions_mogudes', 'excepcions', 'excepcions_resum'} <= d.keys()
    assert all((tmp_path / f'junta.{ext}').stat().st_size for ext in ('json', 'md', 'html'))


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


def test_textos_principals_planers_i_detall_separat():
    b = petita()
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    # També comprovem que resums antics i justificacions internes no es mostren al resum.
    d['com_ho_hem_calculat'] = 'R8 PLAB llindar cota'
    d['excepcions'] = [{}]
    d['excepcions_resum'] = [{'motiu': 'R1-TORN PLAB TE/ PAUL SEM J R8',
                             'nom': 'Grau inventat', 'percentatge': 1, 'sessions': 1}]
    md, html = documents(d)
    principals = (md.split('## Detall tècnic')[0],
                  html.split('<section class="detall-tecnic">')[0])
    for text in principals:
        for cadena in ('R8', 'R1-', 'PLAB', ' J ', 'TE/', 'PAUL', 'SEM', 'llindar', 'cota'):
            assert cadena not in text
    assert '<small>' in md and '<small>' in html
    assert 'R1-TORN PLAB TE/ PAUL SEM J R8' in md.split('## Detall tècnic')[1]
    metode = md.split('## Com ho hem calculat')[1].split('## Detall tècnic')[0]
    assert 3 <= metode.count('.') <= 4


def test_fora_torn_heretades_i_noves(tmp_path):
    b = petita()
    for s in b.sessions.values():
        s.torn = 'tarda'
    p = Proposta.de_base(b)
    # Canviar només l'aula conserva l'horari; canviar dia o hora crea excepció.
    p.files['0'].aula = 'Inventada'
    p.files['1'].h_ini = '09:30'
    p.files['2'].dia = 'M'
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,1|2,Motiu inventat\n')
    d = calcula(p, b, b, colloca(b, p), relax)
    assert d['fora_torn_ja_avui'] == 1
    assert len(d['excepcions']) == 2
    for text in documents(d):
        assert 'Excepcions noves als torns' in text
        assert '1 classes ja es fan avui fora del seu torn i no es toquen.' in text


def test_tarda_i_percentatges_catalans():
    from nivell2.junta import percentatge
    assert percentatge(12) == '12 %'
    assert percentatge(12.5) == '12,5 %'
    b = petita()
    p = Proposta.de_base(b)
    p.files['0'].h_ini = '15:30'
    d = calcula(p, b, b, colloca(b, p))
    assert d['pics']['tarda']['pitjor']['classes'] == 1
    assert d['pics']['tarda']['total_mides'] == 1
    d['sessions_mogudes'][0]['mogudes_pct'] = 12.5
    for text in documents(d):
        assert '12,5 %' in text
        assert '.0%' not in text


def test_documents_cap_curs():
    b = petita()
    p = Proposta.de_base(b)
    for text in documents(calcula(p, b, b, colloca(b, p))):
        assert "Cap curs canvia de dia ni d" in text


@pytest.mark.parametrize('total', [3, 9, 21])
def test_aulari_i_documents_amb_reserva_calculada(total):
    b = petita()
    for i in range(total - len(b.aules)):
        b.aules[f'Extra{i}'] = Aula(f'Extra{i}', '', 'Aules docents', 30)
    b.aules['Seminari'] = Aula('Seminari', '', 'Seminaris', 30)
    assert aulari(b) == {'ordinaries': total, 'reserva': RESERVA,
                         'disponibles': total - RESERVA}
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    maxim = total - RESERVA
    for torn in d['pics'].values():
        assert torn['pitjor']['aules_disponibles'] == maxim
        assert torn['tipica']['aules_disponibles'] == maxim
        assert torn['mides'][0]['oferta_acumulada'] == maxim
    md, html = documents(d)
    assert f"L'aulari té {total} aules ordinàries; en guardem {RESERVA} de reserva per a imprevistos." in md
    for text in (md, html):
        assert f'Per què {maxim} de {maxim} no és prou' in text
        assert f'fer servir les {RESERVA} aules de reserva o a moure classes' in text
        assert 'Recomanem mantenir almenys 1–2 aules lliures' in text
        paragraf = text.split('no és prou')[1].split('Recomanem')[0]
        assert 'R8' not in paragraf and 'PLAB' not in paragraf
    assert f'1/{maxim}' in md and f'1/{maxim}' in html


@pytest.mark.parametrize('nom,escenari', [('5.1', None), ('5.2', None),
                                         ('5.3', CONTINGENCIES), ('5.4', GRAU_NOU)])
def test_cli_escenari_de_cada_proposta(tmp_path, monkeypatch, nom, escenari):
    b = petita()
    crides = []
    def carrega(e):
        crides.append(e)
        return b
    monkeypatch.setattr('nivell2.junta.carrega_oficial', carrega)
    monkeypatch.setattr('nivell2.junta.carrega_model', carrega)
    proposta = Proposta.de_base(b).escriu(tmp_path / nom / 'proposta.csv')
    assert escenari_proposta(nom) == escenari
    assert main([str(proposta), '--sortida', str(tmp_path / 'resum')]) == 0
    assert crides == [escenari, escenari]


def test_files_daltres_semestres_del_mateix_escenari(tmp_path, monkeypatch):
    b = petita()
    completa = deepcopy(b)
    s = deepcopy(b.sessions['0'])
    s.id = 'altre-semestre-inventat'
    completa.sessions[s.id] = s
    p = Proposta.de_base(completa)
    path = p.escriu(tmp_path / 'inventada.csv')
    crides = []
    def carrega(escenari, semestre):
        crides.append((escenari, semestre))
        return completa
    monkeypatch.setattr('nivell2.junta.carrega_oficial', carrega)
    _, col = carrega_proposta(path, b, GRAU_NOU)
    assert set(col) == set(b.sessions)
    assert crides == [(GRAU_NOU, None)]


def test_declarada_sense_canvi_horari_i_heretada_exclosa(tmp_path):
    b = petita()
    for s in b.sessions.values():
        s.torn = 'tarda'
        s.fixada = 'R1: GXX 1r'
    p = Proposta.de_base(b)
    b.sessions['0'].fixada = ''
    p.files['0'].aula = 'Reserva0'
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,0|1|2,Motiu inventat\n')
    d = calcula(p, b, b, colloca(b, p), relax)
    assert [e['id_sessio'] for e in d['excepcions']] == ['0']
    assert d['fora_torn_ja_avui'] == 2
    r, = d['sessions_mogudes']
    assert r['afectades'] == r['aula'] == 1
    assert r['franja'] == 0


def test_pic_instantani_successives_en_aules_diferents():
    b = petita()
    b.sessions['0'].durada = 30
    s = deepcopy(b.sessions['0'])
    s.id, s.ini, s.aula = 'extra', 540, 'Reserva0'
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['simultani']['classes'] == 1
    assert r['pitjor']['classes'] == 2

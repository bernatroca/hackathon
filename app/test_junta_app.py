"""Proves de la pàgina sense servidor ni ports oberts."""
import copy
import json
from pathlib import Path
import sys
from datetime import date
from unittest.mock import patch

import pytest

ARREL = Path(__file__).resolve().parent
sys.path.insert(0, str(ARREL.parent))
sys.path.insert(0, str(ARREL))

from streamlit.testing.v1 import AppTest
from pagines import junta
from nivell2.base import Base, CONTINGENCIES, GRAU_NOU, Proposta, Sessio
from horaris.model import Aula


def dades():
    # Dades sintètiques: cap resultat privat s'incorpora al repositori.
    pic = {'classes': 15, 'aules_disponibles': 19, 'data': '2027-03-08',
           'estimacio': False, 'hora': '10:30', 'setmana': '2027-W10'}
    torn = {'pitjor': pic, 'tipica': pic, 'mides': [
        {'minim_places': 0, 'marge': 4, 'aules_categoria': 19,
         'ocupades_al_pic': 3, 'pic_categoria': 15, 'demanda_acumulada': 15, 'oferta_acumulada': 19}] * 5}
    fila = {'cohort': 'GXX:1r', 'nom': 'Grau inventat, 1r', 'sessions': 10,
            'mogudes': 0, 'mogudes_pct': 0, 'franja': 0, 'franja_pct': 0,
            'aules_assignades': 0, 'aula': 0, 'aula_pct': 0, 'torn': 0, 'torn_pct': 0}
    return {'versio_resum': junta.junta.VERSIO_RESUM, 'versio_calcul': junta.junta.VERSIO_CALCUL,
            'empremtes': {'proposta': 'Avui', 'relaxacions': None}, 'data': '2026-11-07', 'aulari': {'ordinaries': 21, 'reserva': 2, 'disponibles': 19},
            'pics': {'mati': torn, 'tarda': copy.deepcopy(torn)},
            'sessions_mogudes': [fila], 'pitjor_cohort': ['GXX:1r'],
            'fora_torn_ja_avui': 0, 'excepcions': [], 'excepcions_resum': [], 'torn_no_avaluable': 0,
            'com_ho_hem_calculat': 'Segon semestre; canvi de dia, hora o aula.'}


def obre(d, opcions):
    with patch.object(junta, 'disponibles', return_value=opcions), patch.object(junta, 'carrega', return_value=d):
        app = AppTest.from_string("""
import streamlit as st
from pagines import junta
st.title('Resum per a la Junta')
junta.mostra()
""").run(timeout=90)
    assert not app.exception
    assert not app.error
    return app


def test_junta_obre_sense_errors_i_zero_sense_grafic():
    app = obre(dades(), ['Avui', '5.1', '5.2', '5.3', '5.4'])
    assert app.selectbox[0].value == '5.2'
    assert app.selectbox[0].options == ['Avui', 'Aules assignades (5.1)', 'Horari complet (5.2)',
                                       'Amb imprevistos (5.3)', 'Amb el grau nou (5.4)']
    assert any('Cap curs canvia' in m.value for m in app.markdown)
    assert not app.get('plotly_chart')
    assert app.get('download_button')
    assert not app.info


def test_sense_52():
    app = obre(dades(), ['Avui', '5.1'])
    assert app.selectbox[0].value == '5.1'
    assert not any('El resum definitiu sortirà' in i.value for i in app.caption)


def test_percentatges_ordenats_i_absoluts_al_costat():
    d = dades()
    a = d['sessions_mogudes'][0]
    a.update(mogudes=10, mogudes_pct=100, franja=2, franja_pct=20)
    b = dict(a, nom='Titulació petita', sessions=2, mogudes=2, mogudes_pct=100, franja=1, franja_pct=50)
    fig = junta.grafic_mogudes([a, b])
    assert list(fig.data[0].x) == [50, 20]
    assert '1/2 classes' in fig.data[0].text[0]
    assert '50 %' in ''.join(m.value for m in obre(dict(d, sessions_mogudes=[a, b]), ['Avui', '5.2']).markdown)


def test_descobreix_proposta_sense_resum(tmp_path):
    (tmp_path / '5.2').mkdir()
    (tmp_path / '5.2' / 'proposta.csv').touch()
    with patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'SORTIDA', tmp_path):
        assert junta.disponibles() == ['Avui', '5.2']
        with patch.object(junta, 'genera', return_value=dades()) as genera:
            junta.carrega('5.2')
        genera.assert_called_once()


def test_llegeix_resum_existent(tmp_path):
    desti = tmp_path / 'junta'
    desti.mkdir()
    (desti / 'junta.json').write_text(json.dumps(dades()))
    with patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'SORTIDA', tmp_path):
        assert junta.carrega('Avui') == dades()


def test_excepcions_agrupades_i_pic_vermell():
    d = dades()
    d['pics']['tarda']['pitjor'] = dict(d['pics']['tarda']['pitjor'], classes=22)
    d['excepcions'] = [dict(id_sessio=f'S{i}', cohorts=['GXX:1r'],
        torn_requerit='mati', motiu='Motiu compartit', prova='2027-03-08 15:00',
        prova_impossibilitat=None) for i in range(2)]
    app = obre(d, ['Avui'])
    assert any('estat vermell' in m.value for m in app.markdown)
    assert any(e.label == 'Detall tècnic' for e in app.expander)
    assert len(app.dataframe[2].value) == 2


def test_assignacions_no_generen_grafic_i_estimacio_visible():
    d = dades()
    d['sessions_mogudes'][0].update(aules_assignades=10)
    d['pics']['mati']['pitjor']['estimacio'] = True
    app = obre(d, ['Avui', '5.1'])
    assert not app.get('plotly_chart')
    assert any('Estimació' in c.value for c in app.markdown)
    assert app.dataframe[0].value.iloc[0]['Aules assignades'] == 10


def test_resum_antic_es_conserva_per_avisar(tmp_path):
    desti = tmp_path / 'junta'
    desti.mkdir()
    d = dades()
    del d['pics']['mati']['pitjor']['estimacio']
    (desti / 'junta.json').write_text(json.dumps(d))
    with patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'SORTIDA', tmp_path):
        with patch.object(junta, 'genera', return_value=dades()) as genera:
            assert junta.carrega('Avui') == dades()
        genera.assert_called_once()


def test_mides_actuals_i_explicacio():
    d = dades()
    app = obre(d, ['Avui', '5.1'])
    html = ''.join(m.value for m in app.markdown)
    assert html.count('3 de 19') == 5
    assert 'junta-taula' in html
    assert any('alumnes previstos (estimació)' in c.value for c in app.caption)


def test_mides_antigues_avisen(tmp_path):
    desti = tmp_path / 'junta'
    desti.mkdir()
    d = dades()
    for torn in ('mati', 'tarda'):
        for m in d['pics'][torn]['mides']:
            m.pop('ocupades_al_pic', None)
    (desti / 'junta.json').write_text(json.dumps(d))
    with patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'SORTIDA', tmp_path):
        with patch.object(junta, 'genera', return_value=dades()) as genera:
            assert junta.carrega('Avui') == dades()
        genera.assert_called_once()
    app = obre(d, ['Avui'])
    assert any('Resum antic' in i.value for i in app.info)
    assert not app.get('download_button')
    assert not any('<table' in m.value for m in app.markdown)


def test_textos_principals_sense_codis_i_detall_tancat():
    d = dades()
    d['com_ho_hem_calculat'] = 'R8 PLAB llindar cota'
    d['excepcions'] = [dict(id_sessio='S90001', cohorts=['GXX:1r'],
        torn_requerit='mati', motiu='R1-TORN PLAB TE/ PAUL SEM J R8',
        prova='2027-03-08 15:00', prova_impossibilitat=None)]
    app = obre(d, ['Avui', '5.2'])
    detall = next(e for e in app.expander if e.label == 'Detall tècnic')
    assert not detall.proto.expanded
    nodes_tecnics = {id(node) for node in detall}
    for node in app:
        if id(node) in nodes_tecnics:
            continue
        if node.type in ('markdown', 'caption', 'subheader', 'info'):
            text = node.value
        elif node.type == 'arrow_data_frame':
            text = node.value.to_string(index=False)
        else:
            continue
        for cadena in ('R8', 'R1-', 'PLAB', ' J ', 'TE/', 'PAUL', 'SEM', 'llindar', 'cota'):
            assert cadena not in text
    assert any('regla de torn laboratori' in m.value for m in detall.markdown)


def test_quatre_fitxes_i_colors():
    for n, color, text in ((19, 'ambre', 'Sense marge'), (18, 'verd', 'Hi cap'),
                           (17, 'verd', 'Hi cap'), (13, 'verd', 'Hi cap'),
                           (21, 'vermell', 'Falten aules')):
        d = dades()
        d['pics']['mati']['pitjor'] = dict(d['pics']['mati']['pitjor'], classes=n)
        app = obre(d, ['Avui', '5.2'])
        html = next(m.value for m in app.markdown if '<div class="junta-fitxes">' in m.value)
        assert html.count('<section class="junta-fitxa">') == 4
        for titol in ('Matí, hora més plena', 'Tarda, hora més plena', 'Curs més afectat', 'Excepcions noves als torns'):
            assert titol in html
        assert f'{n} <small>de 19 aules' in html
        assert f'estat {color}' in html and text in html
        assert html.count('L&#x27;aulari té 21 aules ordinàries; en guardem 2 de reserva per a imprevistos.') == 2
        assert ('Si una aula falla, cal fer servir la reserva.' in html) == (n == 19)
        assert 'Va just' not in html
        assert 'grid-template-columns:repeat(2,minmax(0,1fr))' in junta.ESTIL
    assert junta.ocupacio(19, 19)[2] == '#e8820c'
    assert '#9a5200' in junta.ESTIL


def test_marge_al_detall_i_fitxes_amb_inventari_diferent():
    d = dades()
    d['aulari'] = {'ordinaries': 9, 'reserva': 2, 'disponibles': 7}
    for torn in d['pics'].values():
        torn['pitjor'] = dict(torn['pitjor'], classes=7, aules_disponibles=7)
    app = obre(d, ['Avui'])
    html = next(m.value for m in app.markdown if '<div class="junta-fitxes">' in m.value)
    assert html.count('9 aules ordinàries') == 2
    assert html.count('Sense marge') == 2
    detall = next(e for e in app.expander if e.label == 'Detall tècnic')
    assert any(s.value == 'Per què 7 de 7 no és prou' for s in detall.subheader)
    assert any('Recomanem mantenir almenys 1–2 aules lliures' in m.value for m in detall.markdown)


@pytest.mark.parametrize('nom,escenari', [('5.1', None), ('5.2', None),
                                         ('5.3', CONTINGENCIES), ('5.4', GRAU_NOU)])
def test_propostes_completes_amb_escenari_inventat(tmp_path, nom, escenari):
    s = Sessio('inventada-' + nom, '100000', 'TE', '81', date(2027, 2, 15),
               'L', 510, 60, 40, 'A', ('GXX:1r',), 'mati', '', frozenset())
    b = Base({s.id: s}, {a: Aula(a, '', 'Aules docents', 50) for a in ('A', 'B', 'C')}, [s.id])
    p = Proposta.de_base(b)
    if nom == '5.3':
        p.files[s.id].data = '2027-02-16'
        p.files[s.id].dia = 'M'
    p.escriu(tmp_path / nom / 'proposta.csv')
    with patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'SORTIDA', tmp_path), \
         patch.object(junta.junta, 'carrega_oficial', return_value=b) as oficial, \
         patch.object(junta.junta, 'carrega_model', return_value=b) as model:
        app = AppTest.from_string("""
from pagines import junta
junta.mostra()
""").run(timeout=90)
        assert app.selectbox[0].value == nom
        assert not app.exception and not app.error and not app.info
        assert app.get('download_button')
        app.radio[0].set_value('Tarda').run()
        assert not app.exception and not app.error
        oficial.assert_called_once_with(escenari)
        model.assert_called_once_with(escenari)
        d = junta.carrega(nom)
        assert d['aulari'] == {'ordinaries': 3, 'reserva': 2, 'disponibles': 1}
        assert d['sessions_mogudes'][0]['franja'] == (1 if nom == '5.3' else 0)


def test_regenera_resum_sense_aulari(tmp_path):
    desti = tmp_path / 'junta' / '5.3'
    desti.mkdir(parents=True)
    d = dades()
    del d['aulari']
    del d['versio_resum']
    (desti / 'junta.json').write_text(json.dumps(d))
    with patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'SORTIDA', tmp_path), \
         patch.object(junta, 'genera', return_value=dades()) as genera:
        assert junta.carrega('5.3') == dades()
        genera.assert_called_once_with('5.3')


def test_barres_vuit_i_desplegable_ordenats():
    d = dades()
    base = d['sessions_mogudes'][0]
    d['sessions_mogudes'] = [dict(base, nom=f'Curs inventat {i}', franja_pct=i * 10) for i in range(10)]
    app = obre(d, ['Avui', '5.2'])
    html = next(m.value for m in app.markdown if 'junta-fila' in m.value and not m.value.startswith('<style>'))
    assert html.count('class="junta-fila"') == 8
    assert html.index('Curs inventat 9') < html.index('Curs inventat 8') < html.index('Curs inventat 2')
    assert 'Curs inventat 1<' not in html
    tots = next(e for e in app.expander if e.label == 'Veure tots els cursos')
    assert not tots.proto.expanded
    assert tots.markdown[0].value.count('class="junta-fila"') == 10


def test_estats_mides_exactes_i_canvi_de_torn():
    d = dades()
    d['pics']['mati']['mides'] = [
        dict(d['pics']['mati']['mides'][0], ocupades_al_pic=n, aules_categoria=1)
        for n in (0, 1, 2, 0, 0)]
    d['pics']['tarda']['mides'] = [
        dict(d['pics']['mati']['mides'][0], ocupades_al_pic=4, aules_categoria=7) for _ in range(5)]
    with patch.object(junta, 'disponibles', return_value=['Avui']), patch.object(junta, 'carrega', return_value=d):
        app = obre(d, ['Avui'])
        html = next(m.value for m in app.markdown if '<table' in m.value)
        assert '0 de 1' in html and 'estat verd' in html
        assert '1 de 1' in html and 'estat ambre' in html and 'Just' in html
        assert '2 de 1' in html and 'estat vermell' in html and 'Falten' in html
        app.radio[0].set_value('Tarda').run()
        assert not app.exception and not app.error
        html = next(m.value for m in app.markdown if '<table' in m.value)
        assert '4 de 7' in html and '0 de 1' not in html


def test_excepcions_noves_i_heretades():
    d = dades()
    d['fora_torn_ja_avui'] = 6
    html = junta.fitxes(d)
    assert '6 classes ja es fan avui fora del seu torn i no es toquen.' in html
    ultima = html.split('<section')[-1]
    assert 'estat verd' in ultima and '>Cap<' in ultima
    d['excepcions'] = [{}]
    assert 'estat ambre' in junta.fitxes(d).split('<section')[-1]


def test_cap_curs_sense_barres_i_decimals():
    d = dades()
    app = obre(d, ['Avui'])
    assert not any('class="junta-fila"' in m.value for m in app.markdown)
    assert not any(e.label == 'Veure tots els cursos' for e in app.expander)
    d['sessions_mogudes'][0].update(franja_pct=12.5, franja=1)
    html = junta.fitxes(d) + junta.barres_cursos(d['sessions_mogudes'])
    assert '12,5 %' in html and '12.5 %' not in html


def test_resum_antic_sense_camp_nou():
    d = dades()
    del d['fora_torn_ja_avui']
    app = obre(d, ['Avui'])
    assert app.info[0].value == 'Resum antic: cal tornar-lo a generar.'
    assert not app.get('download_button')


def test_impacte_canvi_aula_visible_i_ordenat():
    d = dades()
    a = dict(d['sessions_mogudes'][0], nom='Canvi aula', aula=4,
             afectades=4, afectades_pct=40)
    d['sessions_mogudes'].append(a)
    app = obre(d, ['5.2'])
    assert app.dataframe[0].value.iloc[0]['Titulació i curs'] == 'Canvi aula'
    assert app.dataframe[0].value.iloc[0]['Canvi d’aula'] == 4
    assert '40 %' not in junta.fitxes(d)
    assert '>Cap</div>' in junta.fitxes(d)


@pytest.mark.parametrize('font', ['proposta.csv', 'relaxacions.csv'])
def test_sha_canviat_regenera(tmp_path, font):
    p = tmp_path / '5.2' / 'proposta.csv'
    p.parent.mkdir()
    p.write_text('inventada')
    p.with_name('relaxacions.csv').write_text('inventada')
    d = dades()
    d['empremtes'] = junta.junta.empremtes(p)
    desti = tmp_path / 'junta' / '5.2' / 'junta.json'
    junta.junta.escriu_atomic(desti, json.dumps(d))
    with patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'SORTIDA', tmp_path), patch.object(junta, 'genera', return_value=dades()) as gen:
        assert junta.carrega('5.2') == d
        gen.assert_not_called()
        p.with_name(font).write_text('modificada')
        junta.carrega('5.2')
        gen.assert_called_once_with('5.2')


def test_json_truncat_regenera(tmp_path):
    junta.junta.escriu_atomic(tmp_path / 'junta' / 'junta.json', '{')
    with patch.object(junta, 'SORTIDA', tmp_path), patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'genera', return_value=dades()) as gen:
        assert junta.carrega('Avui') == dades()
        gen.assert_called_once()


def test_fallada_actualitzacio_conserva_i_avisa(tmp_path):
    d = dades()
    d['empremtes'] = {}
    d['data'] = '2026-11-07T20:45:00+01:00'
    junta.junta.escriu_atomic(tmp_path / 'junta' / 'junta.json', json.dumps(d))
    with patch.object(junta, 'SORTIDA', tmp_path), patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'genera', side_effect=ValueError('reescriptura')):
        anterior = junta.carrega('Avui')
    app = obre(anterior, ['Avui'])
    assert app.warning[0].value == "Resum de les 20:45; no s'ha pogut actualitzar"


@pytest.mark.parametrize('nom', ['Avui', '5.1', '5.2', '5.3', '5.4'])
def test_totes_opcions_i_torns(nom):
    with patch.object(junta, 'disponibles', return_value=['Avui', '5.1', '5.2', '5.3', '5.4']), patch.object(junta, 'carrega', return_value=dades()):
        app = AppTest.from_string('from pagines import junta; junta.mostra()').run()
        app.selectbox[0].set_value(nom).run()
        for torn in ['Matí', 'Tarda']:
            app.radio[0].set_value(torn).run()
            assert not app.exception and not app.error


def test_motiu_intern_no_surt_al_detall():
    d = dades()
    d['excepcions'] = [dict(id_sessio='S04526', cohorts=['GXX:1r'],
        motiu='impossibilitat demostrada amb R1 dura; vegeu diagnostic.md',
        torn_requerit='tarda', prova='2027-03-08 10:30')]
    app = obre(d, ['5.2'])
    detall = next(e for e in app.expander if e.label == 'Detall tècnic')
    assert all('diagnostic.md' not in m.value for m in detall.markdown)
    assert 'diagnostic.md' not in detall.dataframe[-1].value.to_string()


def test_curs_mes_afectat_només_horari():
    d = dades()
    d['sessions_mogudes'] = [dict(d['sessions_mogudes'][0], nom='Aules', afectades_pct=90),
                            dict(d['sessions_mogudes'][0], nom='Horari', franja_pct=20)]
    html = junta.fitxes(d)
    assert '20 %' in html and '90 %' not in html
    assert '<small>Horari</small>' in html

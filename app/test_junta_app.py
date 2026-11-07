"""Proves de la pàgina sense servidor ni ports oberts."""
import copy
import json
from pathlib import Path
import sys
from unittest.mock import patch

ARREL = Path(__file__).resolve().parent
sys.path.insert(0, str(ARREL.parent))
sys.path.insert(0, str(ARREL))

from streamlit.testing.v1 import AppTest
from pagines import junta


def dades():
    # Dades sintètiques: cap resultat privat s'incorpora al repositori.
    pic = {'classes': 15, 'aules_disponibles': 19, 'data': '2027-03-08',
           'estimacio': False, 'hora': '10:30', 'setmana': '2027-W10'}
    torn = {'pitjor': pic, 'tipica': pic, 'mides': [
        {'minim_places': 0, 'marge': 4, 'aules_categoria': 19,
         'ocupades_al_pic': 3, 'pic_categoria': 15, 'demanda_acumulada': 15, 'oferta_acumulada': 19}] * 5}
    fila = {'cohort': 'GED:1r', 'nom': 'Enginyeria de Dades, 1r', 'sessions': 10,
            'mogudes': 0, 'mogudes_pct': 0, 'franja': 0, 'franja_pct': 0,
            'aules_assignades': 0, 'aula': 0, 'aula_pct': 0, 'torn': 0, 'torn_pct': 0}
    return {'data': '2026-11-07', 'pics': {'mati': torn, 'tarda': copy.deepcopy(torn)},
            'sessions_mogudes': [fila], 'pitjor_cohort': ['GED:1r'],
            'excepcions': [], 'excepcions_resum': [], 'torn_no_avaluable': 0,
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
    app = obre(dades(), ['Avui', '5.1', '5.2'])
    assert app.selectbox[0].value == '5.2'
    assert any('0.0 %' in m.value for m in app.markdown)
    assert not app.get('plotly_chart')
    assert app.get('download_button')
    assert not app.info


def test_sense_52():
    app = obre(dades(), ['Avui', '5.1'])
    assert app.selectbox[0].value == '5.1'
    assert any(i.value == 'El resum definitiu sortirà amb la proposta del 5.2' for i in app.caption)


def test_percentatges_ordenats_i_absoluts_al_costat():
    d = dades()
    a = d['sessions_mogudes'][0]
    a.update(mogudes=10, mogudes_pct=100, franja=2, franja_pct=20)
    b = dict(a, nom='Titulació petita', sessions=2, mogudes=2, mogudes_pct=100, franja=1, franja_pct=50)
    fig = junta.grafic_mogudes([a, b])
    assert list(fig.data[0].x) == [50, 20]
    assert '1/2 classes' in fig.data[0].text[0]
    assert '50.0 %' in ''.join(m.value for m in obre(dict(d, sessions_mogudes=[a, b]), ['Avui', '5.2']).markdown)


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
    d['excepcions'] = [dict(id_sessio=f'S{i}', cohorts=['GED:1r'],
        torn_requerit='mati', motiu='Motiu compartit', prova='2027-03-08 15:00',
        prova_impossibilitat=None) for i in range(2)]
    app = obre(d, ['Avui'])
    assert any('estat vermell' in m.value for m in app.markdown)
    assert any(e.label == 'Detall tècnic' for e in app.expander)
    assert len(app.dataframe[1].value) == 2


def test_assignacions_no_generen_grafic_i_estimacio_visible():
    d = dades()
    d['sessions_mogudes'][0].update(aules_assignades=10)
    d['pics']['mati']['pitjor']['estimacio'] = True
    app = obre(d, ['Avui', '5.1'])
    assert not app.get('plotly_chart')
    assert any('Estimació' in c.value for c in app.markdown)
    assert app.dataframe[0].value.iloc[0]['Aules assignades'] == 10


def test_resum_antic_es_regenera(tmp_path):
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


def test_mides_antigues_es_regeneren(tmp_path):
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
    assert any('R1-TORN PLAB TE/ PAUL SEM J R8' in m.value for m in detall.markdown)


def test_quatre_fitxes_i_colors():
    for n, color, text in ((19, 'ambre', 'Va just'), (13, 'verd', 'Hi cap'),
                           (21, 'vermell', 'Falten aules')):
        d = dades()
        d['pics']['mati']['pitjor'] = dict(d['pics']['mati']['pitjor'], classes=n)
        app = obre(d, ['Avui', '5.2'])
        html = next(m.value for m in app.markdown if '<div class="junta-fitxes">' in m.value)
        assert html.count('<section class="junta-fitxa">') == 4
        for titol in ('Matí, hora més plena', 'Tarda, hora més plena', 'Curs més afectat', 'Excepcions als torns'):
            assert titol in html
        assert f'{n} <small>de 19 aules' in html
        assert f'estat {color}' in html and text in html
        assert 'grid-template-columns:repeat(2,minmax(0,1fr))' in junta.ESTIL
    assert junta.ocupacio(19, 19)[2] == '#e8820c'
    assert '#9a5200' in junta.ESTIL


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

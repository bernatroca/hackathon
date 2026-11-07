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
         'pic_categoria': 15, 'demanda_acumulada': 15, 'oferta_acumulada': 19}] * 5}
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
    assert any('empaten al 0 %' in m.value for m in app.markdown)
    assert not app.get('plotly_chart')
    assert app.get('download_button')
    assert not app.info


def test_sense_52():
    app = obre(dades(), ['Avui', '5.1'])
    assert app.selectbox[0].value == '5.1'
    assert any(i.value == 'El resum definitiu sortirà amb la proposta del 5.2' for i in app.info)


def test_percentatges_ordenats_i_absoluts_al_costat():
    d = dades()
    a = d['sessions_mogudes'][0]
    a.update(mogudes=10, mogudes_pct=100, franja=2, franja_pct=20)
    b = dict(a, nom='Titulació petita', sessions=2, mogudes=2, mogudes_pct=100, franja=1, franja_pct=50)
    fig = junta.grafic_mogudes([a, b])
    assert list(fig.data[0].x) == [50, 20]
    assert '1/2 sessions' in fig.data[0].text[0]
    assert obre(dict(d, sessions_mogudes=[a, b]), ['Avui', '5.2']).get('plotly_chart')


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
    assert any(e.label == 'Veure les dades' for e in app.expander)
    assert app.dataframe[2].value.iloc[0]['Sessions'] == 2
    assert len(app.dataframe[3].value) == 2


def test_assignacions_no_generen_grafic_i_estimacio_visible():
    d = dades()
    d['sessions_mogudes'][0].update(aules_assignades=10)
    d['pics']['mati']['pitjor']['estimacio'] = True
    app = obre(d, ['Avui', '5.1'])
    assert not app.get('plotly_chart')
    assert any('Estimació' in c.value for c in app.caption)
    assert app.dataframe[1].value.iloc[0]['Aules assignades'] == 10


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

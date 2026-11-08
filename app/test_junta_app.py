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


@pytest.fixture(autouse=True)
def resultats_inventats(tmp_path, monkeypatch):
    # També les consultes auxiliars del grau nou queden dins l’escenari inventat.
    monkeypatch.setattr(junta, 'RESULTATS', tmp_path)
    monkeypatch.setattr(junta, 'SORTIDA', tmp_path)


def html_fitxes(app):
    return ''.join(m.value for m in app.markdown if '<section class="junta-fitxa">' in m.value)


def text_visible(app):
    plegats = {id(node) for expander in app.expander for node in expander}
    return '\n'.join(node.value for node in app
                     if id(node) not in plegats and node.type in ('markdown', 'caption', 'subheader', 'info')
                     and not node.value.startswith('<style>'))


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
    assert app.selectbox[0].options == ['Avui', 'Aules assignades', 'Torns nous',
                                       'Resoldre els imprevistos', 'Incorporar el grau nou']
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
    assert '>No</div>' in html_fitxes(app)
    assert 'calen 22 aules de 19' in text_visible(app)
    assert any(e.label == 'Detall tècnic' for e in app.expander)
    assert len(app.dataframe[0].value) == 2


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
    assert 'regla de torn laboratori' in detall.dataframe[-1].value.to_string(index=False)


def test_tres_fitxes_essencials_i_estats_planers():
    for n, resposta in ((19, 'Sí'), (18, 'Sí'), (17, 'Sí'), (13, 'Sí'), (21, 'No')):
        d = dades()
        d['pics']['mati']['pitjor'] = dict(d['pics']['mati']['pitjor'], classes=n)
        app = obre(d, ['Avui', '5.2'])
        html = html_fitxes(app)
        assert html.count('<section class="junta-fitxa">') == 3
        for titol in ('Hi cabem a l’hora més plena?', 'Quantes classes queden fora del seu torn?', 'Quin curs canvia més?'):
            assert titol in html
        assert f'Matí {n} de 19 aules' in html
        assert f'>{resposta}</div>' in html
        assert 'Per saber-ho' in html
        assert 'Cal decidir' in html if n > 19 else 'Resolt amb la proposta' in html
        assert 'aules ordinàries' not in html
        assert len([b for b in app.button if b.label.startswith('Mira ')]) == 3
    assert '#9a5200' in junta.ESTIL


def test_marge_al_detall_i_fitxes_amb_inventari_diferent():
    d = dades()
    d['aulari'] = {'ordinaries': 9, 'reserva': 2, 'disponibles': 7}
    for torn in d['pics'].values():
        torn['pitjor'] = dict(torn['pitjor'], classes=7, aules_disponibles=7)
    app = obre(d, ['Avui'])
    html = html_fitxes(app)
    assert html.count('7 de 7 aules') == 2
    calcul = next(e for e in app.expander if e.label == 'Com ho hem calculat')
    assert any('9 aules ordinàries' in m.value for m in calcul.markdown)
    detall = next(e for e in app.expander if e.label == 'Detall tècnic')
    assert any(s.value == 'Al matí no queda cap aula lliure a l’hora punta' for s in detall.subheader)
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
        desti = tmp_path / 'junta' / nom
        assert all((desti / f'junta.{ext}').exists() for ext in ('json', 'md', 'html'))
        assert d['empremta'] in (desti / 'junta.md').read_text()
        assert d['empremta'] in (desti / 'junta.html').read_text()


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
    assert tots.markdown[0].value.count('class="junta-fila"') == 9


def test_estats_mides_acumulades_i_canvi_de_torn():
    d = dades()
    d['pics']['mati']['mides'] = [
        dict(d['pics']['mati']['mides'][0], ocupades_al_pic=n, aules_categoria=1,
             marge=marge, demanda_acumulada=15, oferta_acumulada=15 + marge)
        for n, marge in ((0, 4), (1, 0), (2, -1), (0, 4), (0, 4))]
    d['pics']['tarda']['mides'] = [
        dict(d['pics']['mati']['mides'][0], ocupades_al_pic=4, aules_categoria=7) for _ in range(5)]
    with patch.object(junta, 'disponibles', return_value=['Avui']), patch.object(junta, 'carrega', return_value=d):
        app = obre(d, ['Avui'])
        html = next(m.value for m in app.markdown if '<table' in m.value)
        assert '0 de 1' in html and 'estat verd' in html
        assert '1 de 1' in html and 'estat ambre' in html and 'Just' in html
        assert '2 de 1' in html and 'estat vermell' in html and 'Falten' in html
        assert '<th>Prou grans</th>' in html and '15 de 14' in html
        app.radio[0].set_value('Tarda').run()
        assert not app.exception and not app.error
        html = next(m.value for m in app.markdown if '<table' in m.value)
        assert '4 de 7' in html and '0 de 1' not in html


def test_excepcions_noves_i_classes_que_es_mantenen():
    d = dades()
    d['fora_torn_ja_avui'] = 6
    html = junta.fitxes(d)
    assert '6 classes ja es fan avui fora del seu torn i no es toquen.' in html
    assert '0 classes noves' in html
    assert 'heretad' not in html
    d['excepcions'] = [{}]
    html = junta.fitxes(d)
    assert '1 classe nova' in html and 'Cal decidir' in html


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
        app = AppTest.from_string('from pagines import junta; junta.mostra()', default_timeout=90).run()
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
    assert '>Horari</div>' in html


def test_fitxa_excepcio_demostrada_i_fixades():
    d = dades()
    d['fixades_tarda'] = 458
    d['excepcions'] = [dict(id_sessio='S04526', cohorts=['GXX:1r'],
        motiu=junta.junta.MOTIU_S04526, torn_requerit='tarda', prova='2027-04-09')]
    app = obre(d, ['5.2'])
    text = ''.join(m.value for m in app.markdown)
    assert '1 excepció nova, demostrada' in text
    assert '458 classes fixades que ja són a la tarda (regla 1)' in text
    assert 'això no demostra' not in text


def test_genera_avui_publica_tres_formats(tmp_path):
    s = Sessio('inventada', '100000', 'TE', '81', date(2027, 2, 15),
               'L', 510, 60, 40, 'A', ('GXX:1r',), 'mati', '', frozenset())
    b = Base({s.id: s}, {'A': Aula('A', '', 'Aules docents', 50)}, [s.id])
    with patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'SORTIDA', tmp_path),          patch.object(junta.junta, 'carrega_oficial', return_value=b),          patch.object(junta.junta, 'carrega_model', return_value=b):
        d = junta.genera('Avui')
        for ext in ('json', 'md', 'html'):
            assert (tmp_path / 'junta' / f'junta.{ext}').exists()
        assert d['empremta'] in (tmp_path / 'junta' / 'junta.md').read_text()


def test_fitxa_mes_afectat_amb_classes_i_comparacio():
    d = dades()
    fila = dict(d['sessions_mogudes'][0], sessions=10, mogudes=10, mogudes_pct=100,
                franja=10, franja_pct=100, torn=10)
    d['sessions_mogudes'] = [dict(fila, cohort=f'GXX:{i}r', nom=f'Grau inventat, {i}r') for i in range(1, 4)]
    d['curs_mes_afectat'] = {'criteri': 'franja', 'curs': d['sessions_mogudes'][0]}
    d.update(fora_torn_avui=30, fora_torn_proposta=1)
    html = junta.fitxes(d)
    assert '100 % de les classes canvien de dia o hora (10 de 10)' in html
    assert 'passen al torn que els toca' in html
    assert 'Avui 30 → 1 amb la proposta, en total.' in html
    assert '>Grau inventat, 1r</div>' in html


def test_mida_exacta_insuficient_amb_aules_grans_lliures():
    d = dades()
    for m in d['pics']['mati']['mides']:
        m.update(ocupades_al_pic=4, aules_categoria=1, marge=3,
                 demanda_acumulada=16, oferta_acumulada=19)
    app = obre(d, ['Avui'])
    html = next(m.value for m in app.markdown if '<table' in m.value)
    assert html.count('4 de 1') == 5
    assert html.count('16 de 19') == 5
    assert 'Falten' not in html and 'Just' not in html
    assert html.count('Hi cap') == 5


def test_sense_textos_repetits_i_data_planera():
    d = dades()
    d['data'] = '2026-11-08T02:07:02+01:00'
    d['excepcions'] = [dict(id_sessio='inventada', cohorts=['GXX:1r'],
                            motiu=junta.junta.MOTIU_S04526,
                            torn_requerit='tarda', prova='2027-04-09')]
    app = obre(d, ['5.2'])
    text = ''.join(m.value for m in app.markdown)
    assert text.count('ho demostra el càlcul') == 1
    assert text.count('1 excepció nova, demostrada') == 1
    assert 'Cas S04526' not in text
    assert not any('les dues primeres fitxes' in m.value for m in app.caption)
    assert any('08/11/2026 02:07' in m.value for m in app.caption)


@pytest.mark.parametrize('nom', ['Avui', '5.1', '5.2', '5.3', '5.4'])
def test_descarrega_identifica_proposta(nom):
    d = dades()
    with patch.object(junta, 'disponibles', return_value=[nom]), patch.object(junta, 'carrega', return_value=d), \
         patch.object(junta.st, 'download_button') as boto:
        app = AppTest.from_string('from pagines import junta; junta.mostra()').run(timeout=90)
    assert not app.exception and not app.error
    assert boto.call_args.kwargs['file_name'] == f'junta-{nom}.html'
    assert junta.NOMS_PROPOSTES[nom] in boto.call_args.args[1]


@pytest.mark.parametrize('bloc,text', [
    ({'grau_nou': {'hi_cap': True, 'sessions_collocades': 2,
                   'sessions_52_mogudes': 0, 'pic_mati_52': 15, 'pic_mati': 16}},
     'Hi cap el grau nou de 40 places: 2 classes col·locades.'),
    ({'vs_52': {'canvis_franja_vs_referencia': 1,
                'canvis_aula_vs_referencia': 3, 'imprevistos': 4}},
     '1 classe canvien de dia o hora i 3 classes més canvien d’aula per 4 imprevistos'),
])
def test_detall_mostra_diferencia_escenari(bloc, text):
    app = obre(dict(dades(), **bloc), ['5.4' if 'grau_nou' in bloc else '5.3'])
    calcul = next(e for e in app.expander if e.label == 'Com ho hem calculat')
    assert not calcul.proto.expanded
    assert text in ''.join(m.value for m in calcul.markdown)


def test_canvi_referencia_invalida_resum(tmp_path):
    proposta = tmp_path / '5.4' / 'proposta.csv'
    proposta.parent.mkdir()
    proposta.write_text('inventada')
    ref = tmp_path / '5.2' / 'proposta.csv'
    ref.parent.mkdir()
    ref.write_text('referencia inventada')
    d = dades()
    d.update(empremtes=junta.junta.empremtes(proposta), empremtes_referencia=junta.junta.empremtes(ref))
    junta.junta.escriu_atomic(tmp_path / 'junta' / '5.4' / 'junta.json', json.dumps(d))
    with patch.object(junta, 'RESULTATS', tmp_path), patch.object(junta, 'SORTIDA', tmp_path), \
         patch.object(junta, 'genera', return_value=dades()) as gen:
        assert junta.carrega('5.4') == d
        gen.assert_not_called()
        ref.write_text('referencia modificada')
        junta.carrega('5.4')
        gen.assert_called_once_with('5.4')


def test_demo_52_mostra_pics_i_grau_nou_sense_canviar_proposta():
    d = dades()
    d['pics']['tarda']['pitjor'] = dict(d['pics']['tarda']['pitjor'], classes=18)
    with patch.object(junta, 'grau_nou_preparat', return_value={
        'hi_cap': True, 'sessions_collocades': 235, 'sessions_52_mogudes': 0}):
        app = obre(d, ['Avui', '5.2', '5.4'])
    assert app.selectbox[0].value == '5.2'
    assert not next(e for e in app.expander if e.label == 'Més opcions').proto.expanded
    html = html_fitxes(app)
    assert html.count('<section class="junta-fitxa">') == 4
    assert 'Matí 15 de 19 aules' in html and 'Tarda 18 de 19 aules' in html
    assert '235 classes col·locades; cap classe de la resta no es mou.' in html
    assert 'Hi cap el grau nou de 40 places?' in html
    assert any('Pas següent: pregunta-ho' in m.value for m in app.markdown)


def test_grau_nou_preparat_rebutja_resum_antic():
    d = dict(dades(), grau_nou={'hi_cap': True},
             empremtes={'proposta': 'nova'}, empremtes_referencia={'proposta': 'ref'})
    with patch.object(junta, 'llegeix', return_value=d), \
         patch.object(junta, 'empremtes', side_effect=lambda n: {'proposta': 'nova' if n == '5.4' else 'ref'}):
        assert junta.grau_nou_preparat() == {'hi_cap': True}
        d['empremtes_referencia'] = {'proposta': 'antiga'}
        assert junta.grau_nou_preparat() is None


def test_camps_nous_junta_i_avui_sense_taules_canvis():
    d = dades()
    d.update(conclusio=['Conclusió inventada per decidir.'], mostrar_canvis=False,
             cursos_afectats=[], fora_torn_avui_compten=20, fora_torn_avui_heretades=12,
             resum_excepcions_aula='Una classe inventada canvia només d’aula.')
    app = obre(d, ['Avui'])
    text = '\n'.join(m.value for m in app.markdown)
    assert 'Conclusió inventada per decidir.' in text
    assert '20 classes que compten i 12 classes fixades que es mantenen' in text
    assert 'classes que compten' not in text_visible(app)
    assert 'Una classe inventada canvia només d’aula.' in text
    assert not app.dataframe


def test_barres_nomes_cursos_afectats():
    fila = dades()['sessions_mogudes'][0]
    html = junta.barres_cursos([fila, dict(fila, nom='Inventat afectat', afectades_pct=10)])
    assert html.count('class="junta-fila"') == 1
    assert 'Inventat afectat' in html


def test_vista_principal_curta_i_detalls_tancats():
    d = dades()
    d.update(conclusio=['VALIDA AMB RELAXACIONS DECLARADES.',
                        'Incompliments R3-AFORAMENT: 9 → 0.'],
             fora_torn_avui=30, fora_torn_proposta=7,
             fora_torn_avui_compten=24, fora_torn_avui_heretades=6,
             fixades_tarda=6)
    d['excepcions'] = [dict(id_sessio='inventada', cohorts=['GXX:1r'],
                            motiu=junta.junta.MOTIU_S04526,
                            torn_requerit='tarda', prova='2027-04-09')]
    app = obre(d, ['5.2'])
    visible = text_visible(app)
    assert 'Aquí tens el resum per decidir si la Junta aprova l’horari proposat' in visible
    assert 'Conclusió: La proposta està comprovada amb les excepcions indicades.' in visible
    assert '1 classe nova' in visible and 'Avui 30 → 7 amb la proposta, en total.' in visible
    assert '6 classes fixades es queden a la tarda' in visible
    assert all(not e.proto.expanded for e in app.expander)
    assert '<table' not in visible and 'junta-fila' not in visible
    assert 'Aules per mida' not in visible and 'Incompliments' not in visible
    for paraula in ('5.1', '5.2', '5.3', '5.4', 'verificador oficial', 'franja original',
                    'heretat', 'heretad', 'sessió', 'R1', 'R3', 'R8', '2027-W'):
        assert paraula not in visible
    calcul = next(e for e in app.expander if e.label == 'Com ho hem calculat')
    assert any('Incompliments R3-AFORAMENT: 9 → 0.' == m.value for m in calcul.markdown)
    assert calcul.radio[0].label == 'Torn'
    assert next(e for e in app.expander if e.label == 'Detall per cursos').dataframe
    assert app.get('download_button')


@pytest.mark.parametrize('boto,detall', [
    ('Mira les aules →', 'Com ho hem calculat'),
    ('Mira les excepcions →', 'Detall tècnic'),
    ('Mira els cursos →', 'Detall per cursos'),
    ('Mira el grau nou →', 'Com ho hem calculat'),
])
def test_botons_obren_el_detall_promes(boto, detall):
    with patch.object(junta, 'disponibles', return_value=['5.2']), \
         patch.object(junta, 'carrega', return_value=dades()), \
         patch.object(junta, 'grau_nou_preparat', return_value={
             'hi_cap': True, 'sessions_collocades': 2, 'sessions_52_mogudes': 0}):
        app = AppTest.from_string('from pagines import junta; junta.mostra()').run(timeout=90)
        assert all(not e.proto.expanded for e in app.expander)
        next(b for b in app.button if b.label == boto).click().run()
    assert not app.exception and not app.error
    assert [e.label for e in app.expander if e.proto.expanded] == [detall]
    assert app.selectbox[0].value == '5.2'
    assert app.get('download_button')


def test_curs_mes_afectat_respecta_el_camp_del_resum_sense_inventar_motiu():
    d = dades()
    d['sessions_mogudes'][0].update(franja=10, franja_pct=100)
    d['curs_mes_afectat'] = {'criteri': 'aula', 'curs': dict(d['sessions_mogudes'][0],
        nom='Curs del resum', sessions=4, aula=3, aula_pct=75)}
    html = junta.fitxes(d)
    assert '>Curs del resum</div>' in html
    assert '75 % de les classes canvien d’aula (3 de 4)' in html
    assert '100 %' not in html
    assert 'passen al torn' not in html and 'per fer encaixar' not in html


def test_grau_nou_sense_cabuda_no_es_presenta_com_a_resolt():
    grau = {'hi_cap': False, 'sessions_collocades': 1, 'sessions_52_mogudes': 2}
    html = junta.peces_fitxes(dades(), grau)[-1]['html']
    assert '>No</div>' in html and 'Cal decidir' in html
    assert '1 classe col·locada' in html
    assert '2 classes de la resta es mouen' in html
    assert 'Resolt amb la proposta' not in html

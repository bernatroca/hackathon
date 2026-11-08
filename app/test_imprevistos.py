"""Proves Streamlit amb dades inventades, sense carregar el paquet real."""
from copy import deepcopy
from pathlib import Path
import re
import sys
from unittest.mock import patch

ARREL = Path(__file__).resolve().parent
for carpeta in (ARREL.parent, ARREL):
    if str(carpeta) not in sys.path:
        sys.path.insert(0, str(carpeta))

from streamlit.testing.v1 import AppTest
from pagines import imprevistos
from prova_imprevistos import dades_inventades


def test_normalitza_assignatura_mojibake_inventat():
    assert imprevistos.normalitza_assignatura("Bases dâ€™Experimentació") == "Bases d’Experimentació"
    assert imprevistos.normalitza_assignatura("Organització i Gestió d\x92Empreses") == "Organització i Gestió d’Empreses"
    assert imprevistos.normalitza_assignatura("Assignatura d'Exemple") == "Assignatura d’Exemple"


def obre(dades=None):
    app = AppTest.from_string("""
import streamlit as st
from pagines import imprevistos
st.title('Imprevistos')
imprevistos.mostra(st.session_state.dades_inventades)
""")
    app.session_state['dades_inventades'] = dades if dades is not None else dades_inventades()
    with patch.object(imprevistos, 'carrega', side_effect=AssertionError('La prova no pot carregar dades.')):
        app.run(timeout=30)
    assert not app.exception
    assert not app.error
    return app


def contingut(app):
    return '\n'.join(m.value for m in app.markdown if not m.value.startswith('<style>'))


def test_pagina_resum_quatre_targetes_i_taula_llegible():
    app = obre()
    html = contingut(app)
    assert [t.value for t in app.title] == ['Imprevistos']
    assert 'Comprovat amb el verificador oficial' in html
    assert 'en 1,24 segons' in html
    assert html.count('<article class="imp-targeta">') == 4
    assert html.count('Resolt amb excepció') == 1
    assert html.count('class="estat verd"') == 4  # Veredicte i tres targetes.
    assert 'class="estat ambre"' in html
    assert all(t['titol'] in html for t in dades_inventades()['imprevistos'])
    assert not re.search(r'\b(R[1-8](?:-[A-Z]+)?|TE|PAUL|SEM|PLAB)\b', html)
    taula = app.dataframe[0].value
    assert list(taula.columns) == ['Assignatura', 'Grup', 'Data', 'Hora', 'Aula', 'Dia/hora nous', 'Motiu']
    assert len(taula) == 6
    assert any('Subgrup' in g for g in taula['Grup'])
    assert app.expander[0].label == 'Detall tècnic'
    assert not app.expander[0].proto.expanded
    assert app.code[0].value == 'python -m nivell2.s53 --temps 120 --llavor 0'


def test_filtres_natius_per_imprevist_i_classes_de_suport():
    app = obre()
    for clau, n in [('aula_reservada', 1), ('grup_creix', 2), ('aula_avariada', 1),
                   ('recuperacio', 1), ('suport', 1), ('totes', 6)]:
        app.button(key='imp-boto-' + clau).click().run(timeout=30)
        assert not app.exception
        assert not app.error
        assert len(app.dataframe[0].value) == n
    app.button(key='imp-boto-recuperacio').click().run(timeout=30)
    fila = app.dataframe[0].value.iloc[0]
    assert fila['Data'] == '18/02/2027 (cancel·lada)'
    assert '19/02/2027' in fila['Dia/hora nous']


def test_sense_canvis_i_filtre_sense_files():
    dades = dades_inventades()
    dades['files'] = []
    app = obre(dades)
    assert any('No hi ha classes que canviïn' in m.value for m in app.info)
    assert not any(b.key == 'imp-boto-suport' for b in app.button)
    app.button(key='imp-boto-aula_reservada').click().run(timeout=30)
    assert not app.exception
    assert any('No hi ha classes que canviïn' in m.value for m in app.info)


def test_resultats_absents_i_incomplets_sense_excepcio_visible(tmp_path):
    paths = tuple(tmp_path / f'fitxer-inventat-{i}' for i in range(6))
    with patch.object(imprevistos, '_fitxers', return_value=paths), \
            patch.object(imprevistos, '_carrega', side_effect=AssertionError('No ha de carregar.')):
        assert imprevistos.carrega() is None
        app = AppTest.from_string('from pagines import imprevistos\nimprevistos.mostra()').run(timeout=30)
        assert not app.exception
        assert app.info[0].value == 'Encara no hi ha la proposta d’imprevistos'
        assert app.code[0].value == imprevistos.ORDRE
        paths[1].touch()
        app.run(timeout=30)
        assert not app.exception
        assert len(app.error) == 1
        assert not app.info


def test_veredicte_no_validat_no_es_presenta_com_resolt():
    for valor in ('NO VALIDA', ''):
        dades = dades_inventades()
        dades['resum']['veredicte'] = valor
        dades['resum']['temps_s'] = None
        app = obre(dades)
        html = contingut(app)
        assert 'Comprovat amb el verificador oficial' not in html
        assert 'Resolt' not in html
        assert 'Pendent de comprovació' in html
        assert 'Temps no disponible' in html


def test_html_escapa_els_textos_de_les_targetes():
    dades = dades_inventades()
    dades['imprevistos'][0]['descripcio'] = '<script>prova inventada</script>'
    dades['imprevistos'][0]['motius'] = ['<b>motiu inventat</b>']
    html = contingut(obre(dades))
    assert '<script>' not in html
    assert '&lt;script&gt;prova inventada&lt;/script&gt;' in html
    assert '&lt;b&gt;motiu inventat&lt;/b&gt;' in html


def test_actualitzacio_dels_fitxers_invalida_cache(tmp_path):
    paths = tuple(tmp_path / f'fitxer-inventat-{i}' for i in range(6))
    for p in paths:
        p.touch()
    with patch.object(imprevistos, '_fitxers', return_value=paths), \
            patch.object(imprevistos, '_carrega', return_value=dades_inventades()) as carrega:
        imprevistos.carrega()
        versions = carrega.call_args.args[1]
        paths[2].write_text('Excepció inventada')
        imprevistos.carrega()
        assert carrega.call_args.args[0] == tuple(map(str, paths))
        assert carrega.call_args.args[1][2] != versions[2]


def test_prova_autonoma_no_accedeix_a_dades_reals():
    with patch.object(imprevistos, 'carrega', side_effect=AssertionError('Prova només inventada.')), \
            patch.object(imprevistos, '_fitxers', side_effect=AssertionError('Prova només inventada.')):
        app = AppTest.from_file(str(ARREL / 'prova_imprevistos.py')).run(timeout=30)
    assert not app.exception
    assert not app.error
    assert app.title[0].value == 'Imprevistos'
    assert len(app.dataframe[0].value) == 6
    assert any('MOSTRA' in m.value for m in app.caption)


def test_pagina_navegable_executa_el_fitxer_sense_titol_duplicat():
    with patch.object(imprevistos, 'carrega', return_value=dades_inventades()):
        app = AppTest.from_string("""
import streamlit as st
from pathlib import Path
from pagines import imprevistos
pagina = st.navigation([st.Page(Path(imprevistos.__file__), title='Imprevistos', url_path='imprevistos')])
st.title(pagina.title)
pagina.run()
""").run(timeout=30)
    assert not app.exception
    assert not app.error
    assert len(app.title) == 1
    assert 'Comprovat amb el verificador oficial' in contingut(app)


def test_concordanca_targetes_resum_i_suport():
    for n, afectades, canvi, suport in (
        (0, 'cap classe afectada', 'cap classe canvia', 'cap classe més es mou'),
        (1, '1 classe afectada', '1 classe canvia', '1 classe més es mou'),
        (2, '2 classes afectades', '2 classes canvien', '2 classes més es mouen'),
        (3, '3 classes afectades', '3 classes canvien', '3 classes més es mouen'),
    ):
        dades = dades_inventades()
        dades['resum'].update(canvis_aula_vs_referencia=n, canvis_franja_vs_referencia=n,
                              classes_de_suport=n)
        dades['imprevistos'][0].update(sessions_afectades=n, canvis_aula=n, canvis_franja=0)
        app = obre(dades)
        text = re.sub('<[^>]+>', '', contingut(app))
        assert afectades in text
        assert canvi + ' d’aula' in text
        assert canvi + ' de dia o hora' in text
        assert imprevistos.accio(n, 0) in text
        assert suport + ' per fer lloc' in text
        assert sum('Per provar un imprevist nou' in c.value for c in app.caption) == 1
        assert not any('per fer lloc' in c.value for c in app.caption)
        assert '0 canvien' not in text and '0 classes' not in text
    assert imprevistos.accio(1, 0) == 'Què hem fet: 1 canvia d’aula i cap de dia o hora.'
    assert imprevistos.accio(2, 1) == 'Què hem fet: 2 canvien d’aula i 1 de dia o hora.'


def test_filtres_sense_canvis_diuen_cap():
    dades = dades_inventades()
    dades['files'] = []
    app = obre(dades)
    assert all(b.label.endswith('(cap)') for b in app.button)


def test_temps_un_segon_en_singular():
    dades = dades_inventades()
    dades['resum']['temps_s'] = 1
    html = contingut(obre(dades))
    assert 'en 1,00 segon<' in html
    assert 'en 1,00 segons' not in html


def test_informe_ha_de_correspondre_al_csv(tmp_path):
    import hashlib
    import json
    import pytest
    proposta, informe = tmp_path/'proposta.csv', tmp_path/'informe.json'
    proposta.write_text('id_sessio,dia,h_ini,aula\ninventada,L,15:00,Q9/0001\n')
    report = {'veredicte': 'VALIDA', 'context': {
        'proposta_sha256': hashlib.sha256(proposta.read_bytes()).hexdigest()}}
    informe.write_text(json.dumps(report))
    assert imprevistos._informe_validat(informe, proposta) == report
    proposta.write_text('id_sessio,dia,h_ini,aula\n')
    with pytest.raises(ValueError, match='CSV actual'):
        imprevistos._informe_validat(informe, proposta)
    informe.write_text('{"veredicte": "VALIDA"}')
    with pytest.raises(ValueError, match='CSV actual'):
        imprevistos._informe_validat(informe, proposta)


def test_canvis_csv_i_oficials_i_suport_explicats():
    dades = dades_inventades()
    dades['resum'].update(canvis_aula_vs_referencia=54, canvis_aula_oficials=53,
                          canvis_aula_recuperades=1, classes_de_suport=2)
    html = contingut(obre(dades))
    assert 'La proposta canvia l’aula de 54 classes' in html
    assert 'el verificador en compta 53' in html
    assert 'classe cancel·lada' in html
    assert '2 classes més es mouen per fer lloc a les afectades' in html
    assert 'només movem' not in html
    assert imprevistos.veredicte({'veredicte': 'NO VALIDA'})[0] == 'vermell'


def test_motius_tecnics_nomes_dins_del_detall():
    from nivell2.imprevistos import MOTIUS_PLANERS, MOTIU_DESCONEGUT
    for original in [*MOTIUS_PLANERS, 'R9: motiu desconegut; vegeu diagnostic.md i CSV']:
        dades = dades_inventades()
        from nivell2.imprevistos import motiu_planer
        dades['imprevistos'][0]['motius'] = [motiu_planer(original)]
        dades['resum']['relaxacions_per_motiu'] = [{'motiu': original, 'sessions': 1}]
        app = obre(dades)
        exterior = contingut(app)
        assert original not in exterior
        assert not re.search(r"\b(?:R\d+|CSV|TE|PAUL|SEM|PLAB)\b|diagnostic\.md", exterior)
        assert "'" not in re.sub(r'<[^>]+>', '', exterior)
        assert app.expander[0].dataframe[0].value.iloc[0]['Motiu'] == motiu_planer(original)


def test_nota_recompte_concorda_i_es_dinamica():
    for n, oficials, recuperades, fragment in [
        (1, 0, 1, '1 classe;'),
        (7, 5, 2, '7 classes;'),
    ]:
        dades = dades_inventades()
        dades['resum'].update(canvis_aula_vs_referencia=n, canvis_aula_oficials=oficials,
                              canvis_aula_recuperades=recuperades)
        html = contingut(obre(dades))
        assert fragment in html
        assert f'el verificador en compta {oficials}' in html
        if recuperades == 2:
            assert 'les 2 classes cancel·lades que recuperem' in html


def test_targeta_mostra_recompte_del_motiu_i_text_avaluacio_compartit():
    from nivell2.test_imprevistos import escenari
    from nivell2.imprevistos import calcula, MOTIUS_PLANERS, motiu_planer
    from nivell2.junta import MOTIU_S04526
    for n in (1, 2):
        for original in (next(iter(MOTIUS_PLANERS)), 'Motiu desconegut inventat.'):
            b, c, p, q, noms = escenari()
            p.files['creix-inventada'].aula = 'Q9/0001'
            p.files['suport-inventada'].aula = 'Q9/0001'
            ids = ['reserva-inventada', 'creix-inventada'][:n]
            avaluacio = next(m for m in MOTIUS_PLANERS if m.startswith('Setmana'))
            rows = [{'restriccio': 'R7-PLAB', 'sessions': '|'.join(ids), 'justificacio': original},
                    {'restriccio': 'R1-TORN', 'sessions': 'avaria-inventada', 'justificacio': avaluacio}]
            app = obre(calcula(b, c, p, q, rows, noms=noms))
            html = contingut(app)
            assert '3 classes afectades' in html
            assert motiu_planer(original, n) in html
            assert MOTIU_S04526 in html
            assert original not in html
            assert avaluacio not in html


def test_taula_destaca_aula_motiu_i_no_repeteix_la_franja_sense_canvi():
    app = obre()
    assert app.button(key='imp-boto-totes').label == 'Totes les classes (6)'
    taula = app.dataframe[0].value
    assert 'Q9/0001 → Q9/1003' in set(taula['Aula'])
    assert 'Per fer lloc' in set(taula['Motiu'])
    app.button(key='imp-boto-grup_creix').click().run(timeout=30)
    assert not app.error
    assert 'Dia/hora nous' not in app.dataframe[0].value
    assert set(app.dataframe[0].value['Aula']) == {'Q9/0002 → Q9/1003'}


def test_dades_absents_mostren_instruccions_abans_dimportar_pagines(tmp_path):
    import os
    with patch.dict(os.environ, {'REPTE_DIR': str(tmp_path)}), \
            patch('streamlit.navigation', side_effect=AssertionError('No ha d’importar les pàgines.')):
        app = AppTest.from_file(str(ARREL / 'app.py')).run(timeout=30)
    assert not app.exception
    assert len(app.error) == 1
    assert 'repte/repte-horaris-escola/' in app.error[0].value
    assert 'REPTE_DIR' in app.error[0].value
    assert app.button(key='reintenta-paquet').label == 'Torna-ho a provar'


def test_error_unic_per_renderitzat_i_reintent_buida_totes_les_caches():
    import servei
    app = AppTest.from_string("""
import streamlit as st
from errors import mostra_error
st.session_state['_error_mostrat'] = False
for _ in range(10):
    mostra_error()
""")
    with patch.object(servei.connexio, 'cache_clear') as duckdb_clear, \
            patch.object(servei.st.cache_data, 'clear') as streamlit_clear:
        app.run(timeout=30)
        assert not app.exception
        assert len(app.error) == 1
        assert len(app.button) == 1
        app.button(key='reintenta-dades').click().run(timeout=30)
        assert not app.exception
        assert len(app.error) == 1
        duckdb_clear.assert_called_once()
        streamlit_clear.assert_called_once()


def test_setmanes_filtren_residuals_i_tipica_no_en_te_en_compte():
    from datetime import date
    import duckdb
    import servei
    from nivell1 import dades
    con = duckdb.connect()
    con.execute('CREATE TABLE sessions (setmana VARCHAR, data DATE, sem INTEGER)')
    for setmana, dia, n in [('2027-W07', '2027-02-15', 200),
                             ('2027-W08', '2027-02-22', 210),
                             ('2027-W09', '2027-03-01', 220),
                             ('2027-W10', '2027-03-08', 1),
                             ('2027-W11', '2027-03-15', 2)]:
        con.execute('INSERT INTO sessions SELECT ?, CAST(? AS DATE), 2 FROM range(?)', [setmana, dia, n])
    servei.setmanes.clear()
    try:
        with patch.object(servei, 'connexio', return_value=con), patch.object(dades, 'connexio', return_value=con):
            assert servei.setmanes(2) == [('2027-W07', date(2027, 2, 15), 200),
                                         ('2027-W08', date(2027, 2, 22), 210),
                                         ('2027-W09', date(2027, 3, 1), 220)]
            assert dades.setmana_tipica(2) == '2027-W08'
            assert servei.setmanes(1) == []
            con.execute('DELETE FROM sessions WHERE setmana NOT IN (?, ?)', ['2027-W10', '2027-W11'])
            assert dades.setmana_tipica(2) == '2027-W10'
    finally:
        servei.setmanes.clear()
        con.close()


def test_opcions_nomes_a_pagines_davui_i_dates_llegibles(tmp_path):
    from datetime import date
    import os
    from types import SimpleNamespace as NS
    import servei
    (tmp_path / 'paquet').mkdir()
    (tmp_path / 'paquet' / 'sessions.csv').touch()
    (tmp_path / 'horaris').mkdir()
    for ruta, error in [('avui', False), ('respostes', False), ('part2', False),
                        ('junta', False), ('imprevistos', False), ('avui', True)]:
        pagina = NS(url_path=ruta, title='Pàgina inventada', run=lambda: None)
        with patch.dict(os.environ, {'REPTE_DIR': str(tmp_path)}), \
                patch('streamlit.navigation', return_value=pagina), \
                patch.object(servei, 'versio_registre', return_value=()), \
                patch.object(servei, 'setmanes', return_value=[('2027-W07', date(2027, 2, 15), 250)],
                             side_effect=RuntimeError('Error inventat') if error else None), \
                patch('components.vistes.franja_context', return_value='Context inventat'), \
                patch('xat.widget.posa_widget'), patch('xat.widget.pantalla_actual', return_value={}):
            app = AppTest.from_file(str(ARREL / 'app.py')).run(timeout=30)
        assert not app.exception
        if error:
            assert len(app.error) == 1
            assert not app.sidebar.error
            assert app.button(key='reintenta-dades').label == 'Torna-ho a provar'
            assert not app.sidebar.expander[0].button
            continue
        assert not app.error
        assert any(b.label == 'Actualitza les dades' for b in app.sidebar.button)
        if ruta in ('avui', 'respostes'):
            assert [e.label for e in app.sidebar.expander] == ['Opcions']
            assert app.sidebar.selectbox[1].options == ['Típica', 'Setmana del 15 de febrer · 250 classes']
        else:
            assert not app.sidebar.selectbox
            assert not app.sidebar.expander
            assert any(c.value == 'La proposta és del 2n semestre' for c in app.sidebar.caption)

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
    assert list(taula.columns) == ['Assignatura', 'Grup', 'Abans', 'Després']
    assert len(taula) == 6
    assert any('Subgrup' in g for g in taula['Grup'])
    assert app.expander[0].label == 'Detall tècnic'
    assert not app.expander[0].proto.expanded
    assert app.code[0].value == 'python -m nivell2.s53 --temps 40 --llavor 0'


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
    assert '18/02/2027' in fila['Abans']
    assert '19/02/2027' in fila['Després']


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
        if n:
            assert any(suport + ' per fer lloc' in c.value for c in app.caption)
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
    assert 'El CSV inclou 54 canvis' in html
    assert 'El verificador en compta 53' in html
    assert 'classe cancel·lada' in html
    assert '2 classes més es mouen per fer lloc a les afectades' in html
    assert 'només movem' not in html
    assert imprevistos.veredicte({'veredicte': 'NO VALIDA'})[0] == 'vermell'

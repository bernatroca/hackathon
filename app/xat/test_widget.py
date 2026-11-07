"""Proves sense ports, amb context inventat."""
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from xat import widget


@pytest.fixture(autouse=True)
def neteja_cache():
    widget._api.clear()
    yield
    widget._api.clear()


def test_arrenca_un_sol_cop_i_endpoint():
    with patch('xat.servidor.arrenca', create=True, return_value='http://localhost:8502') as arrenca:
        assert widget._api() == 'http://localhost:8502/api/xat'
        assert widget._api() == 'http://localhost:8502/api/xat'
        arrenca.assert_called_once_with()


def test_endpoint_complet():
    with patch('xat.servidor.arrenca', create=True, return_value='http://localhost:8502/api/xat/'):
        assert widget._api() == 'http://localhost:8502/api/xat'


def test_injeccio_inline_context_segura_i_guardes():
    pantalla = dict(resum='Inventat', text='</script><script>alert(1)</script>', preguntes=['Una?'])
    with patch.object(widget, '_api', return_value='http://localhost:8502/api/xat'), patch.object(widget.st, 'html') as html:
        widget.posa_widget(pantalla)
        primer = html.call_args.args[0]
        widget.posa_widget(None)
        segon = html.call_args.args[0]
    assert primer != segon
    assert html.call_args.kwargs == {'unsafe_allow_javascript': True}
    assert "if (!window.XatIA)" in primer
    assert "getElementById('xatia-estil')" in primer
    assert 'window.XatIA.pantalla(' in primer
    assert 'window.XatIA.pantalla(null)' in segon
    assert '<script>alert(1)' not in primer
    assert '\\u003c/script\\u003e' in primer
    assert primer.count('</script>') == 1
    assert '<iframe' not in primer
    assert 'localStorage' in primer


def test_backend_absent_no_trenca_app():
    with patch.object(widget, '_api', side_effect=AttributeError('arrenca')), patch.object(widget.st, 'html') as html:
        widget.posa_widget(None)
    assert 'data:application/json,' in html.call_args.args[0]
    assert '%22teClau%22%3Afalse' in html.call_args.args[0]


def test_context_grup_i_aula_sense_arrossegar_altres_pagines():
    estat = {'semestre': 1, 'setmana': 'inventada', 'p2-proposta': '5.2',
             'p2-vista': 'Proposta i avui', 'p2-titulacio': 'GXX', 'p2-curs': '1r',
             'p2-grup': '81', 'p2-aula': 'Q9/0001', 'p2-setmana': None}
    p = widget.pantalla_actual('Horari proposat', estat)
    assert p['resum'] == 'Horari proposat · 5.2 · GXX 1r 81'
    assert 'Q9/0001' in p['text']
    assert 'Semestre 2. Setmana: típica.' in p['text']
    p = widget.pantalla_actual('Com estem avui', estat)
    assert 'GXX' not in p['text']
    assert '5.2' not in p['text']
    assert p['preguntes'][0] == 'Quantes sessions són al torn equivocat?'
    estat['p2-vista'] = 'Només avui'
    assert '5.2' not in widget.pantalla_actual('Horari proposat', estat)['text']


def test_preguntes_i_junta():
    assert len(widget.pantalla_actual('Imprevistos', {})['preguntes']) == 2
    assert widget.pantalla_actual('Totes les respostes', {})['preguntes'] == widget.PER_DEFECTE
    assert '5.4' in widget.pantalla_actual('Resum per a la Junta', {'junta-proposta': '5.4'})['text']

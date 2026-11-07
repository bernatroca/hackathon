from datetime import date
from pathlib import Path
import sys

ARREL = Path(__file__).resolve().parent
sys.path.insert(0, str(ARREL.parent))
sys.path.insert(0, str(ARREL))

import unittest
from unittest.mock import patch
from contextlib import contextmanager


@contextmanager
def raises(error, match):
    try:
        yield
    except error as exc:
        assert match in str(exc)
    else:
        raise AssertionError("No s’ha produït l’error esperat")
from nivell2.base import Base, Sessio, Proposta, Assignacio
from components.graella import (celles_grup, celles_aula, exporta_aula_html,
    setmana_tipica, grups, taula_html, FRANGES)


def sessio(sid, tipus='TE', grup='TE/81', data=date(2027, 3, 8), **kwargs):
    valors = dict(id=sid, codi='100001', tipus=tipus, grup=grup, data=data,
        dia='L', ini=510, durada=60, alumnes=20, aula='Q9/0001',
        cohorts=('GXX:1r',), torn='mati', fixada='', docents=frozenset())
    valors.update(kwargs)
    return Sessio(**valors)


def crea_base():
    sessions = [sessio('S90001'), sessio('S90002', 'PAUL', 'PAUL/811'),
        sessio('S90003', 'SEM', 'SEM/813'), sessio('S90004', grup='TE/914'),
        sessio('S90005', 'PLAB', 'PLAB/905'),
        sessio('S90006', data=date(2027, 3, 15))]
    return Base({s.id: s for s in sessions}, {})


@contextmanager
def app_inventada():
    """Cap prova nova de pàgina depèn de les dades del repte."""
    from tempfile import TemporaryDirectory
    from streamlit.testing.v1 import AppTest
    base = crea_base()
    base.sessions['S90001'].aula = ''
    tercer = sessio('S90020', cohorts=('GXX:3r',), ini=900)
    base.sessions[tercer.id] = tercer
    proposta = Proposta.de_base(base)
    proposta.files['S90001'].aula = 'Q9/0001'
    proposta.files['S90002'].h_ini = '10:00'
    with TemporaryDirectory(dir=ARREL.parent) as carpeta:
        arrel = Path(carpeta)
        (arrel / '5.2').mkdir()
        (arrel / '5.2' / 'proposta.csv').touch()
        with patch('pagines.part2.RESULTATS', arrel), \
             patch('pagines.part2.carrega_dades', return_value=(base, {'100001': 'Assignatura Inventada'}, {'GXX': 'Grau inventat'})), \
             patch('pagines.part2.carrega_proposta', return_value=proposta):
            yield AppTest.from_string('from pagines.part2 import mostra\nmostra()').run(timeout=30)


class TestGraella(unittest.TestCase):
    def test_grup_i_linies(self):
        base = crea_base()
        p = Proposta.de_base(base)
        assert grups(base)['GXX']['1r']['81'] == '81'
        assert {c.id_sessio for c in celles_grup(base, p, date(2027, 3, 10), 'GXX', '1r', '81')} == {'S90001', 'S90002', 'S90003'}


    def test_aula_canvis_i_relaxacio(self):
        base = crea_base()
        p = Proposta.de_base(base)
        p.files['S90001'] = Assignacio('M', '09:15', 'Q9/0002')
        c, = celles_aula(base, p, date(2027, 3, 8), 'Q9/0002', relaxacions={'S90001': ['Motiu declarat']})
        assert c.canvi_franja and c.canvi_aula and c.ini == 555 and c.fi == 615
        assert c.relaxacions == ('Motiu declarat',)
        assert 'Motiu declarat' in taula_html([c])
        assert '09:15–10:15' in taula_html([c])
        assert len(FRANGES) == 25 and FRANGES[-1] == 1230


    def test_recuperacio_canvia_setmana(self):
        base = crea_base()
        p = Proposta.de_base(base)
        p.files['S90001'] = Assignacio('V', '10:30', 'Q9/0002', '2027-03-19')
        assert not celles_aula(base, p, date(2027, 3, 8), 'Q9/0002')
        assert celles_aula(base, p, date(2027, 3, 15), 'Q9/0002')[0].canvi_franja


    def test_html_autonom_i_escapat(self):
        base = crea_base()
        p = Proposta.de_base(base)
        html = exporta_aula_html(base, p, date(2027, 3, 8), 'Q9/0001', noms={'100001': '<script>alert(1)</script>'})
        assert '<!doctype html>' in html and '<style>' in html and 'lang="ca"' in html
        assert '<script>' not in html and '&lt;script&gt;' in html
        assert 'Dilluns' in html and '20:30–21:00' in html


    def test_incompleta_i_dia_incorrecte(self):
        base = crea_base()
        p = Proposta.de_base(base)
        del p.files['S90001']
        with raises(ValueError, match='absents'):
            celles_aula(base, p, date(2027, 3, 8), 'Q9/0001')
        p = Proposta.de_base(base)
        p.files['S90001'].dia = 'Z'
        with raises(ValueError, match='Dia incorrecte'):
            celles_aula(base, p, date(2027, 3, 8), 'Q9/0001')


    def test_tipica_mediana_i_desempat(self):
        base = crea_base()
        assert setmana_tipica(base) == date(2027, 3, 8)


    def test_pagina_sense_errors(self):
        with app_inventada() as at:
            assert not at.exception and not at.error
            assert at.selectbox(key='p2-proposta').label == 'Proposta'
            assert at.selectbox(key='p2-curs').label == 'Curs'
            at.selectbox(key='p2-setmana').select(date(2027, 3, 15)).run(timeout=30)
            assert not at.exception and not at.error

    def test_consulta_actual_i_guia(self):
        with app_inventada() as at:
            at.get('button_group')[0].set_value('Només avui').run(timeout=30)
            assert not at.exception and not at.error
            html = '\n'.join(m.value for m in at.markdown)
            assert html.count('<table class="horari"') == 2
            assert 'Amb la proposta ·' not in html
            assert 'Aula no indicada a les dades' in html
            at.selectbox(key='p2-curs').select('3r').run(timeout=30)
            assert not at.exception and not at.error
            at.button(key='p2-inicia-guia').click().run(timeout=30)
            assert any(c.value == 'Guia · Pas 1 de 6' for c in at.caption)
            for pas in range(2, 7):
                at.button(key='p2-guia-seguent').click().run(timeout=30)
                assert not at.exception and not at.error
                assert any(c.value == f'Guia · Pas {pas} de 6' for c in at.caption)
            at.button(key='p2-guia-seguent').click().run(timeout=30)
            assert not any(c.value.startswith('Guia · Pas') for c in at.caption)

class TestMillores(unittest.TestCase):
    def test_bloc_unic_dues_hores_i_solapament(self):
        from components.graella import Cella
        a = Cella('S90007', 'L', 510, 630, 'Q9/0001', 'Assignatura Inventada I', 'Teoria', '81', False, False)
        b = Cella('S90008', 'L', 555, 615, 'Q9/0002', 'Assignatura Inventada II', 'Problemes', '811', False, False)
        html = taula_html([a, b])
        assert html.count('<b>Assignatura Inventada I</b>') == 1
        assert html.count('<b>Assignatura Inventada II</b>') == 1
        assert 'rowspan="6"' in html  # Inclou els límits exactes 09:15 i 10:15.
        assert 'colspan="2">Dilluns' in html
        assert '08:30–10:30' in html

    def test_classe_sola_aprofita_amplada_del_dia(self):
        from components.graella import Cella
        from html.parser import HTMLParser

        class Graella(HTMLParser):
            def __init__(self):
                super().__init__()
                self.celles = []
            def handle_starttag(self, tag, attrs):
                if tag == 'td':
                    self.celles.append(dict(attrs))

        cs = [Cella('S90001', 'L', 510, 630, 'Q9/0001', 'Assignatura Inventada I', 'Teoria', '81', False, False),
              Cella('S90009', 'L', 630, 690, 'Q9/0001', 'Assignatura Inventada II', 'Problemes', '811', False, False),
              Cella('S90010', 'L', 630, 690, 'Q9/0002', 'Assignatura Inventada III', 'Problemes', '812', False, False)]
        p = Graella()
        p.feed(taula_html(cs))
        sessions = [a for a in p.celles if 'rowspan' in a]
        assert sessions == [{'rowspan': '4', 'colspan': '2'},
                            {'rowspan': '2', 'colspan': '1'}, {'rowspan': '2', 'colspan': '1'}]

    def test_proposta_defecte(self):
        from pagines.part2 import proposta_per_defecte, RESULTATS
        from nivell2.base import RESULTATS_PRINCIPAL
        assert RESULTATS is RESULTATS_PRINCIPAL
        assert proposta_per_defecte(['Avui', '5.1', '5.2', '5.4']) == '5.2'
        assert proposta_per_defecte(['Avui', '5.1']) == '5.1'
        assert proposta_per_defecte(['Avui', '5.4']) == 'Avui'

    def test_resum_grup(self):
        from components.graella import resum_grup
        base = crea_base()
        avui = Proposta.de_base(base)
        p = Proposta.de_base(base)
        p.files['S90001'] = Assignacio('M', '15:00', 'Q9/0002')
        p.files['S90002'] = Assignacio('L', '08:30', 'Q9/0002')
        args = (date(2027, 3, 8), 'GXX', '1r', '81')
        actuals = celles_grup(base, avui, *args)
        noves = celles_grup(base, p, *args)
        resum = resum_grup(base, p, actuals, noves)
        assert '1 classes canvien de dia o d’hora' in resum
        assert '2 canvien d’aula' in resum
        assert '1 canvien de torn' in resum
        assert '1 avui → 2 a la proposta' in resum
        p.files['S90001'].data = '2027-03-19'
        assert '1 classes canvien de dia o d’hora' in resum_grup(base, p, actuals, celles_grup(base, p, *args))

    def test_excepcio_calendari_escapada(self):
        from tempfile import TemporaryDirectory
        from pagines.part2 import carrega_excepcions
        with TemporaryDirectory(dir=ARREL.parent) as carpeta:
            path = Path(carpeta) / 'excepcions.csv'
            path.write_text('id_sessio,data,minut_inici,motiu\nS90001,2027-03-08,510,Festiu <especial>\n')
            motius = carrega_excepcions(str(path), 1)
        base = crea_base()
        dades = celles_grup(base, Proposta.de_base(base), date(2027, 3, 8), 'GXX', '1r', '81', relaxacions=motius)
        html = taula_html(dades)
        assert 'classe relaxada' in html
        assert 'Excepció de calendari' in html
        assert 'Festiu &lt;especial&gt;' in html


class TestAssignacions(unittest.TestCase):
    def test_llegenda_i_etiquetes_sense_codis(self):
        from components.graella import Cella, llegenda_html
        c = Cella('S90001', 'L', 510, 570, '', 'Assignatura Inventada I', 'Teoria', 'TE/81', False, False)
        html = taula_html([c], originals=True)
        assert 'Grup 81' in html and 'TE/81' not in html
        assert 'Aula no indicada a les dades' in html
        assert 'Pendent d’assignar aula' in taula_html([c])
        assert all(t in llegenda_html() for t in ('Sense canvis', 'Aula assignada', 'Canvia', 'Cas especial'))

    # Simula una aula a traslladar sense codificar noms reals de l'inventari.
    @patch('components.graella.a_traslladar', lambda aula: aula == 'Q9/0004')
    def test_aula_assignada_neutra(self):
        from components.graella import resum_grup
        base = crea_base()
        base.sessions['S90001'].aula = ''
        base.sessions['S90002'].aula = 'Q9/0004'
        base.sessions['S90003'].sense_espai = True
        avui = Proposta.de_base(base)
        p = Proposta.de_base(base)
        for sid in ('S90001', 'S90002', 'S90003'):
            p.files[sid].aula = 'Q9/0002'
        args = (date(2027, 3, 8), 'GXX', '1r', '81')
        actuals = celles_grup(base, avui, *args)
        noves = celles_grup(base, p, *args)
        assert sum(c.canvi for c in noves) == 0
        assert sum(c.aula_assignada for c in noves) == 1
        html = taula_html(noves)
        assert 'Aula assignada' in html and 'class="classe canvi' not in html
        assert 'class="classe aula-nova"' in html
        resum = resum_grup(base, p, actuals, noves)
        assert '0 canvien d’aula' in resum and '1 amb aula assignada' in resum


class TestRedisseny(unittest.TestCase):
    def test_controls_unics_i_titol_amb_espai(self):
        from pagines.part2 import CSS_PAGINA
        with app_inventada() as at:
            grup = at.selectbox(key='p2-grup')
            assert grup.label == 'Grup' and grup.options == ['Grup 81', 'Grup 914']
            assert not grup.disabled
            assert at.selectbox(key='p2-titulacio').disabled
            assert not at.selectbox(key='p2-curs').disabled
            assert any(h.value == 'La setmana del grup' for h in at.subheader)
            assert not any(h.value.startswith('3.') for h in at.subheader)
            at.selectbox(key='p2-grup').select('914').run(timeout=30)
            at.selectbox(key='p2-curs').select('3r').run(timeout=30)
            grup = at.selectbox(key='p2-grup')
            assert grup.label == 'Grup' and grup.options == ['Grup 81']
            assert grup.disabled
            assert not at.exception and not at.error
        assert '.st-key-p2-graelles{margin-top:24px;' in CSS_PAGINA

    def test_carrils_nomes_al_dia_i_franja_amb_solapament(self):
        from dataclasses import replace
        from html.parser import HTMLParser
        from components.graella import Cella, CSS

        class Taula(HTMLParser):
            def __init__(self):
                super().__init__()
                self.files = []
            def handle_starttag(self, tag, attrs):
                if tag == 'tr':
                    self.files.append([])
                elif tag in ('th', 'td'):
                    self.files[-1].append(dict(attrs))

        a = Cella('S90001', 'L', 510, 570, '', 'Inventada', 'Teoria', '81', False, False)
        cs = [a, replace(a, id_sessio='S90002', ini=600, fi=660),
              replace(a, id_sessio='S90003', ini=600, fi=660)]
        cs += [replace(a, id_sessio=f'S9001{i}', dia=dia) for i, dia in enumerate('MXJV')]
        html = taula_html(cs)
        taula = Taula()
        taula.feed(html)
        assert [int(c.get('colspan', 1)) for c in taula.files[0]] == [1, 2, 1, 1, 1, 1]
        assert 'min-width:990px' in html  # Dos carrils dilluns; un als altres dies.
        # La primera classe de dilluns ocupa tot el dia, les simultànies un carril.
        blocs = [c for fila in taula.files[1:] for c in fila if 'rowspan' in c and 'colspan' in c]
        assert [int(c['colspan']) for c in blocs] == [2, 1, 1, 1, 1, 1, 1]
        # Simulem els rowspans: cada fila ha de tenir exactament les mateixes
        # set columnes, també després del final de les classes paral·leles.
        pendents = [0] * 7
        for fila in taula.files[1:]:
            ocupades = [n > 0 for n in pendents]
            seguent = [max(0, n - 1) for n in pendents]
            for cella in fila:
                col = ocupades.index(False)
                ample = int(cella.get('colspan', 1))
                assert col + ample <= 7 and not any(ocupades[col:col + ample])
                for k in range(col, col + ample):
                    ocupades[k] = True
                    seguent[k] = int(cella.get('rowspan', 1)) - 1
            assert all(ocupades)
            pendents = seguent
        assert not any(pendents)
        assert 'min-width:140px' in CSS
        assert '.horari-scroll{overflow:auto;width:100%;max-width:100%;min-width:0;contain:inline-size;' in CSS

    def test_classes_consecutives_no_obren_carrils_per_arrodoniment(self):
        from dataclasses import replace
        from components.graella import Cella
        a = Cella('S90001', 'L', 510, 555, '', 'Inventada I', 'Teoria', '81', False, False)
        b = replace(a, id_sessio='S90002', ini=555, fi=615, assignatura='Inventada II')
        html = taula_html([a, b])
        assert 'min-width:840px' in html
        assert 'colspan="1">Dilluns' in html
        assert '09:15–10:15' in html
        assert html.count('<details class="classe') == 2
        # Un sol minut compartit sí que exigeix dos blocs de com a mínim 140 px.
        html = taula_html([a, replace(b, ini=554)])
        assert 'min-width:990px' in html and 'colspan="2">Dilluns' in html

    def test_colors_variables_i_prioritat(self):
        from dataclasses import replace
        from components.graella import Cella, CSS, ESTATS, estat_cella
        c = Cella('S90001', 'L', 510, 570, 'Q9/0001', 'Inventada', 'Teoria', '81', False, False)
        casos = [(c, 'igual'), (replace(c, aula_assignada=True), 'aula-nova'),
                 (replace(c, canvi_aula=True), 'canvi'),
                 (replace(c, canvi_franja=True, setmana_diferent=True), 'relaxada'),
                 (replace(c, aula_assignada=True, relaxacions=('Excepció inventada',)), 'relaxada')]
        for cella, esperat in casos:
            assert estat_cella(cella) == esperat
            assert f'data-estat="{esperat}"' in taula_html([cella])
        assert ESTATS['igual'][2] == 'var(--blau,#2a78d6)'
        assert 'border-left:5px solid var(--blau,#2a78d6)' in CSS
        assert 'var(--verd,#2f8f46)' in CSS and 'var(--verd-fons,#e9f4ec)' in CSS
        assert 'var(--verd-text,#1f6b33)' in CSS and 'var(--vermell,' in CSS
        assert 'var(--p2-taronja,' in CSS
        assert '<svg' in taula_html([casos[1][0]])

    def test_filtre_apaga_sense_amagar_ni_recolocar(self):
        from dataclasses import replace
        from components.graella import Cella, recomptes_estat
        a = Cella('S90001', 'L', 510, 570, '', 'Inventada I', 'Teoria', '81', False, False)
        b = replace(a, id_sessio='S90002', ini=570, fi=630, aula='Q9/0001', aula_assignada=True)
        html = taula_html([a, b], filtre='aula-nova')
        assert 'class="classe apagada" data-estat="igual"' in html
        assert 'class="classe aula-nova" data-estat="aula-nova"' in html
        assert html.count('<details class="classe') == 2
        assert 'apagada"' not in taula_html([a, b], filtre='totes')
        assert recomptes_estat([a, b]) == {'igual': 1, 'aula-nova': 1}
        with app_inventada() as at:
            at.button(key='p2-boto-aula-nova').click().run(timeout=30)
            assert not at.exception and not at.error
            assert at.button(key='p2-boto-aula-nova').proto.type == 'primary'
            assert 'apagada"' in '\n'.join(m.value for m in at.markdown)
            at.button(key='p2-boto-totes').click().run(timeout=30)
            assert 'apagada"' not in '\n'.join(m.value for m in at.markdown)

    def test_compartida_un_bloc_en_grup_aula_i_exportacio(self):
        from components.graella import recomptes_estat
        a = sessio('S90001', compartida='C90001', codi='100000')
        b = sessio('S90002', compartida='C90001', codi='100001')
        base = Base({a.id: a, b.id: b}, {})
        p = Proposta.de_base(base)
        noms = {'100000': 'Inventada I', '100001': 'Inventada II'}
        grup = celles_grup(base, p, date(2027, 3, 8), 'GXX', '1r', '81', noms=noms)
        aula = celles_aula(base, p, date(2027, 3, 8), 'Q9/0001', noms=noms)
        for html in (taula_html(grup), taula_html(aula), exporta_aula_html(base, p, date(2027, 3, 8), 'Q9/0001', noms=noms)):
            assert html.count('<details class="classe') == 1
            assert 'Inventada I / Inventada II' in html
            assert html.count('Classe compartida') == 1
        assert recomptes_estat(aula) == {'igual': 1}
        p.files['S90002'].aula = 'Q9/0002'
        assert taula_html(celles_grup(base, p, date(2027, 3, 8), 'GXX', '1r', '81')).count('<details class="classe') == 2
        p.files['S90002'].aula = 'Q9/0001'
        p.files['S90002'].h_ini = '09:30'
        assert taula_html(celles_aula(base, p, date(2027, 3, 8), 'Q9/0001')).count('<details class="classe') == 2

    def test_noms_grups_i_amplada_per_carril(self):
        from components.graella import Cella, CSS, nom_grup
        assert nom_grup('TE/912', 'Teoria') == 'Grup 912 · teoria'
        assert nom_grup('PAUL/903', 'Problemes') == 'Subgrup 903 · problemes'
        assert nom_grup('SEM/906', 'Seminari') == 'Subgrup 906 · seminari'
        cs = [Cella(f'S90{i:03}', 'L', 510, 570, '', 'Assignatura Inventada', 'Problemes', f'PAUL/904{i}', False, False) for i in range(4)]
        html = taula_html(cs)
        assert 'min-width:1290px' in html  # 90 + (4 carrils + 4 dies) * 150
        assert html.count('<col style="width:150px">') == 8
        assert 'min-width:140px' in CSS and 'overflow:auto' in CSS
        assert 'overflow-wrap:anywhere' not in CSS and 'word-break:normal' in CSS
        assert 'PAUL/' not in html

    def test_torn_unic_i_detall_accessible(self):
        base = Base({'S90001': sessio('S90001', ini=900)}, {})
        p = Proposta.de_base(base)
        p.files['S90001'] = Assignacio('M', '16:00', 'Q9/0002')
        c, = celles_grup(base, p, date(2027, 3, 8), 'GXX', '1r', '81')
        html = taula_html([c])
        assert '08:30–09:00' not in html and '16:00–16:30' in html
        assert '20:30–21:00' in html
        assert 'Abans: dilluns 15:00' in html
        assert '<summary>' in html and 'title="Abans:' in html

    def test_resum_inclou_classe_que_marxa_de_la_setmana(self):
        from pagines.part2 import resum_html
        base = crea_base()
        avui, proposta = Proposta.de_base(base), Proposta.de_base(base)
        proposta.files['S90001'] = Assignacio('V', '16:00', 'Q9/0002', '2027-03-19')
        args = date(2027, 3, 8), 'GXX', '1r', '81'
        html = resum_html(base, proposta, celles_grup(base, avui, *args), celles_grup(base, proposta, *args), True)
        assert '<b>1</b><span>canvis d’hora' in html
        assert '<b>1</b><span>canvis d’aula' in html

    def test_guia_passos_enfocament_i_posicio_al_costat(self):
        import json
        import shutil
        import subprocess
        from components.ajuda_part2 import PASSOS, POSICIO_JS
        from pagines.part2 import CSS_PAGINA
        assert len(PASSOS) == 6
        assert all(selector.startswith('.st-key-p2-') and titol and text for selector, titol, text in PASSOS)
        assert 'position:fixed;left:18px;bottom:18px' in CSS_PAGINA
        assert 'box-shadow:0 0 0 100vmax' in CSS_PAGINA
        assert 'outline:3px solid var(--blau)' in CSS_PAGINA
        assert 'prefers-reduced-motion' in CSS_PAGINA
        with app_inventada() as at:
            at.button(key='p2-inicia-guia').click().run(timeout=30)
            components = at.get('iframe')
            assert len(components) == 1
            scripts = components[0].proto.srcdoc
            assert '<script>' in scripts and 'window.parent' in scripts
            assert 'const document=window.document' in scripts
            assert components[0].proto.tab_index == -1
            assert "e.key==='Escape'" in scripts
            assert "panell.focus({preventScroll:true})" in scripts
            assert "getBoundingClientRect" in scripts and "ResizeObserver" in scripts
            at.button(key='p2-guia-tanca').click().run(timeout=30)
            assert not any(c.value.startswith('Guia · Pas') for c in at.caption)
        node = shutil.which('node')
        if not node:
            self.skipTest('Node no disponible per executar la geometria JavaScript')
        script = POSICIO_JS + '''
console.log(JSON.stringify([
  posicioPanell({left:30,right:500,top:100,bottom:250},350,200,1280,800),
  posicioPanell({left:280,right:1100,top:100,bottom:250},350,200,1280,800),
  posicioPanell({left:10,right:370,top:100,bottom:250},350,200,390,800),
  posicioPanell({left:30,right:1100,top:650,bottom:750},350,200,1280,800),
  posicioPanell({left:30,right:1100,top:650,bottom:750},350,200,390,800)
]));'''
        resultat = subprocess.run([node, '-e', script], check=True, capture_output=True, text=True)
        dreta, sota, estret, damunt, estret_baix = json.loads(resultat.stdout)
        assert dreta == {'mode': 'dreta', 'left': 512, 'top': 100, 'width': 350}
        assert sota['mode'] == 'sota' and sota['top'] > 250
        assert estret['mode'] == 'estret' and estret['width'] == 366
        assert damunt['mode'] == 'damunt' and damunt['top'] + 200 < 650
        assert estret_baix['top'] + 200 <= 788

    def test_javascript_del_component_enfoca_segueix_i_tanca(self):
        import json
        import shutil
        import subprocess
        from components.ajuda_part2 import PASSOS
        node = shutil.which('node')
        if not node:
            self.skipTest('Node no disponible per executar el JavaScript de la guia')
        scripts = []
        with app_inventada() as at:
            at.button(key='p2-inicia-guia').click().run(timeout=30)
            for pas, (selector, _, _) in enumerate(PASSOS):
                component, = at.get('iframe')
                assert f'const selector={json.dumps(selector)}, pas={pas};' in component.proto.srcdoc
                scripts.append(component.proto.srcdoc.removeprefix('<script>').removesuffix('</script>'))
                at.button(key='p2-guia-seguent').click().run(timeout=30)
                assert not at.exception and not at.error
            scripts.append(at.get('iframe')[0].proto.srcdoc.removeprefix('<script>').removesuffix('</script>'))
        # DOM sintètic: executem el codi que ha emès la pàgina, amb dos windows
        # diferents, per detectar accessos accidentals al document de l'iframe.
        harness = r'''
const assert = require('node:assert/strict');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
function events(obj) {
  obj.listeners = {};
  obj.addEventListener = (name, f) => (obj.listeners[name] ??= new Set()).add(f);
  obj.removeEventListener = (name, f) => obj.listeners[name]?.delete(f);
  obj.dispatch = (name, event) => [...(obj.listeners[name] ?? [])].forEach(f => f(event));
  return obj;
}
const parentRect = {left:20, top:30};
const parent = {scrollLeft:0, scrollTop:0, getBoundingClientRect:()=>parentRect};
function element(rect={left:30,right:500,top:100,bottom:250}) {
  const classes = new Set();
  return {isConnected:true, offsetParent:parent, offsetHeight:200,
    style:{}, dataset:{}, attrs:{}, rect, focused:0,
    classList:{add:c=>classes.add(c), remove:c=>classes.delete(c), contains:c=>classes.has(c)},
    getBoundingClientRect(){return this.rect;},
    setAttribute(k,v){this.attrs[k]=v;},
    focus(){this.focused++;}, scrollIntoView(){}};
}
const targets = input.selectors.map(()=>element());
const panel = element(), launcher = element(), start = element();
let closed = 0;
const close = {click:()=>closed++};
const map = Object.fromEntries(input.selectors.map((s,i)=>[s,targets[i]]));
Object.assign(map, {'.st-key-p2-guia':panel, '.st-key-p2-obre-guia':launcher,
  '.st-key-p2-guia-tanca button':close, '.st-key-p2-inicia-guia button':start});
const page = {querySelector:s=>map[s], querySelectorAll:()=>targets.filter(t=>t.classList.contains('p2-pas-actiu'))};
const doc = events({querySelector:s=>s==='.st-key-p2-pagina'?page:undefined});
class Observer {observe(){} disconnect(){}}
const host = events({document:doc, innerWidth:1280, innerHeight:800,
  ResizeObserver:Observer, MutationObserver:Observer, matchMedia:()=>({matches:true}),
  requestAnimationFrame:f=>{f();return 1;}, cancelAnimationFrame:()=>{}});
const window = {parent:host}; // El fill no té document ni mides ni observadors.
globalThis.addEventListener = ()=>{};
for (let i=0; i<input.selectors.length; i++) {
  eval(input.scripts[i]);
  assert.equal(targets.filter(t=>t.classList.contains('p2-pas-actiu')).length,1);
  assert.ok(targets[i].classList.contains('p2-pas-actiu'));
  assert.equal(panel.attrs.role,'dialog');
  assert.equal(panel.focused,i+1);
  assert.equal(Number.parseFloat(panel.style.left)+parentRect.left,512);
  targets[i].rect.right=540;
  doc.dispatch('scroll');
  assert.equal(Number.parseFloat(panel.style.left)+parentRect.left,552);
  assert.equal(doc.listeners.keydown.size,1);
  assert.equal(host.listeners.resize.size,2);
}
host.innerWidth=390;
host.dispatch('resize');
assert.equal(panel.dataset.posicio,'estret');
assert.equal(panel.style.width,'366px');
assert.equal(Number.parseFloat(panel.style.left)+parentRect.left,12);
let prevented=false;
doc.dispatch('keydown',{key:'Escape',preventDefault:()=>prevented=true});
assert.ok(prevented);
assert.equal(closed,1);
assert.equal(start.focused,1);
eval(input.scripts.at(-1));
assert.equal(targets.filter(t=>t.classList.contains('p2-pas-actiu')).length,0);
assert.equal(doc.listeners.keydown.size,0);
assert.equal(host.listeners.resize.size,1);
'''
        resultat = subprocess.run([node, '-e', harness], input=json.dumps({
            'scripts': scripts, 'selectors': [p[0] for p in PASSOS]}),
            check=False, capture_output=True, text=True)
        assert resultat.returncode == 0, resultat.stderr

    def test_navegacio_seccions_i_paths(self):
        import ast
        arbre = ast.parse((ARREL / 'app.py').read_text())
        crida = next(n for n in ast.walk(arbre) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'navigation')
        assert [n.value for n in crida.args[0].keys] == ['Com està l’horari', 'La proposta', 'Ajuda']
        pagines = [n for n in ast.walk(crida) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'Page']
        titols = [next(k.value.value for k in n.keywords if k.arg == 'title') for n in pagines]
        assert 'Horari proposat' in titols
        assert [k.value.value for n in pagines for k in n.keywords if k.arg == 'url_path'] == ['avui', 'respostes', 'part2', 'junta']

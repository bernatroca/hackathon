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


def contingut_graella(html):
    """Separa el contingut de la graella dels estils de l'exportació."""
    return html.split('</style>', 1)[-1]


def sense_marques_nom(html):
    """Text dels noms sense els embolcalls visuals de paraula."""
    import re
    return re.sub(r'<span class="nom-paraula">(.*?)</span>', r'\1', html)


def estructura_graella(html):
    from html.parser import HTMLParser

    class Graella(HTMLParser):
        def __init__(self):
            super().__init__()
            self.dies, self.classes, self.hores, self.caps = [], [], [], []
            self.dia = None

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            classes = attrs.get('class', '').split()
            if 'dia-horari' in classes:
                self.dia = attrs
                self.dies.append(attrs)
            if 'classe' in classes:
                self.classes.append((self.dia, attrs))
            if 'hora' in classes:
                self.hores.append(attrs)
            if 'dia-cap' in classes and 'hora-cap' not in classes:
                self.caps.append(attrs)

    graella = Graella()
    graella.feed(html)
    return graella


def posicio_classe(attrs):
    import re
    fila, durada, columna, ample = map(int, re.search(
        r'grid-row:(\d+)/span (\d+);grid-column:(\d+)/span (\d+)', attrs['style']).groups())
    return fila, fila + durada, columna, columna + ample


class TestGraellaResponsive(unittest.TestCase):
    def test_dia_sencer_amb_mati_tarda_i_setmana_buida(self):
        from dataclasses import replace
        from components.graella import Cella
        mati = Cella('INVENTADA-MATI', 'L', 548, 803, '', 'Assignatura Inventada',
                     'Teoria', 'TE/81', False, False)
        tarda = replace(mati, id_sessio='INVENTADA-TARDA', ini=905, fi=1010, dia='X')
        for classes in ([mati], [tarda], [mati, tarda], []):
            graella = estructura_graella(taula_html(classes))
            assert [int(h['data-minut']) for h in graella.hores] == list(range(510, 1261, 30))
            assert len(graella.dies) == 5
        buit = taula_html([])
        assert 'No hi ha classes aquesta setmana.' in buit and 'class="horari"' in buit

    def test_linies_continues_alineades_amb_files_exactes(self):
        from components.graella import Cella, CSS
        c = Cella('INVENTADA-LINIES', 'L', 555, 645, '', 'Assignatura Inventada',
                  'Teoria', 'TE/81', False, False)
        html = taula_html([c])
        graella = estructura_graella(html)
        assert [h['class'] for h in graella.hores[:4]] == ['hora', 'hora hora-plena', 'hora', 'hora hora-plena']
        assert posicio_classe(graella.classes[0][1]) == (46, 136, 1, 2)
        assert '--files:repeat(750,1.6px)' in html
        assert '#efeee9 0 1px,transparent 1px 48px,#d9d8d2 48px 49px' in html
        assert '.dia-horari{column-gap:6px;background-image:var(--linies)' in CSS
        assert 'background-position:0 6px' in CSS
        assert 'tbody' not in CSS and '<td' not in html
        assert 'position:sticky;left:0' in CSS

    def test_linies_comencen_amb_el_color_de_la_mitja_hora(self):
        from components.graella import Cella
        c = Cella('INVENTADA-MITJA', 'L', 510, 630, '', 'Assignatura Inventada',
                  'Teoria', 'TE/81', False, False)
        html = taula_html([c])
        assert '#efeee9 0 1px,transparent 1px 48px,#d9d8d2 48px 49px' in html
        assert [h['class'] for h in estructura_graella(html).hores[:4]] == [
            'hora', 'hora hora-plena', 'hora', 'hora hora-plena']

    def test_apostrof_tipografic_i_recte_sense_perdre_text(self):
        from html.parser import HTMLParser
        from components.graella import Cella, CSS

        class Noms(HTMLParser):
            def __init__(self):
                super().__init__()
                self.dins = False
                self.noms = []

            def handle_starttag(self, tag, attrs):
                if tag == 'b':
                    self.dins = True

            def handle_endtag(self, tag):
                if tag == 'b':
                    self.dins = False

            def handle_data(self, data):
                if self.dins:
                    self.noms.append(data)

        for nom in ('Desenvolupament d’aplicacions per a Enginys Inventats',
                    "Disseny d'aparells per a Entorns Inventats"):
            c = Cella('INVENTADA-APOSTROF', 'L', 570, 690, '', nom,
                      'Teoria', 'TE/81', False, False)
            parser = Noms()
            parser.feed(contingut_graella(taula_html([c])))
            assert ''.join(parser.noms) == nom
        assert 'font-family:system-ui,sans-serif' in CSS
        assert 'word-spacing:normal' in CSS and 'letter-spacing:normal' in CSS
        with app_inventada() as at:
            html = '\n'.join(m.value for m in at.markdown)
            assert 'Desenvolupament d&#8217;aplicacions per a Enginys Inventats' in sense_marques_nom(html)
            assert not at.exception and not at.error

    def test_curs_desconegut_descriptiu_i_al_final(self):
        with app_inventada() as at:
            curs = at.selectbox(key='p2-curs')
            assert curs.options == ['1r', '3r', 'Sense curs a les dades']
            assert '?' not in curs.options
            curs.select('?').run(timeout=30)
            assert at.selectbox(key='p2-curs').value == '?'
            assert not at.exception and not at.error

    def test_guia_compartida_a_la_capa_superior(self):
        from components.ajuda_part2 import CSS_GUIA, LLANCADOR_JS, prova_guia_html
        from components.prova_graella import genera
        from pagines.part2 import CSS_PAGINA
        html = genera()
        assert CSS_GUIA in html and CSS_GUIA in CSS_PAGINA
        assert LLANCADOR_JS in html
        assert "obre.setAttribute('popover','manual')" in LLANCADOR_JS
        assert 'obre.showPopover()' in LLANCADOR_JS
        assert 'z-index:2147483646' in CSS_GUIA
        assert 'min-height:44px' in CSS_GUIA
        assert 'container:contingut / inline-size' in html
        assert 'padding-top:64px' in html and 'menu-plegat' in html
        assert 'Com funciona? Guia pas a pas' in prova_guia_html()
        assert 'prova-obre-menu' in html and 'data-testid="stSidebar"' in html

    def test_columnes_i_posicions_exactes_de_la_setmana(self):
        from dataclasses import replace
        from components.graella import Cella
        from components.prova_graella import setmana_inventada
        a = Cella('INVENTADA-A', 'L', 510, 555, '', 'Assignatura Inventada',
                  'Problemes', 'PAUL/811', False, False)
        parcials = [a, replace(a, id_sessio='INVENTADA-B', ini=540, fi=600),
                    replace(a, id_sessio='INVENTADA-C', ini=600, fi=660)]
        for classes in (setmana_inventada(), parcials):
            graella = estructura_graella(taula_html(classes))
            assert len(graella.dies) == 5 and len(graella.classes) == len(classes)
            inici = 510
            for dia, attrs in graella.classes:
                fila, final, col, dret = posicio_classe(attrs)
                assert 1 <= col < dret <= int(dia['data-carrils']) + 1
                assert any(c.ini - inici + 1 == fila and c.fi - inici + 1 == final for c in classes)
                for altre_dia, altre in graella.classes:
                    if attrs is altre or dia is not altre_dia:
                        continue
                    f, fi, k, ample = posicio_classe(altre)
                    assert not (fila < fi and f < final and col < ample and k < dret)

    def test_setmana_seguida_fins_divendres_sense_duplicar_classes(self):
        from components.graella import Cella, NOMS_DIES
        from components.prova_graella import setmana_inventada
        divendres = Cella('INVENTADA-DIVENDRES', 'V', 570, 630, '',
                         'Classe de divendres', 'Teoria', 'TE/99', False, False)
        for classes in (setmana_inventada(), [divendres]):
            html = taula_html(classes)
            graella = estructura_graella(html)
            assert html.count('class="horari"') == 1
            assert tuple(d['aria-label'] for d in graella.dies) == NOMS_DIES
            assert len(graella.caps) == 5
            assert len(graella.classes) == len(classes)
            assert all(sense_marques_nom(html).count('<b>' + c.assignatura + '</b>') == 1 for c in classes if '’' not in c.assignatura)

    def test_noms_sencers_i_colors_amb_contrast(self):
        from components.graella import CSS, ESTATS
        from components.prova_graella import setmana_inventada
        classes = setmana_inventada()
        html = taula_html(classes)
        from html import unescape
        for c in classes:
            assert f'<b>{c.assignatura}</b>' in unescape(sense_marques_nom(html))
        assert '…' not in html  # El text complet roman al DOM; el CSS aplica l'el·lipsi.
        assert 'text-overflow:ellipsis' in CSS
        assert 'hyphens:none' in CSS and 'word-break:normal' in CSS
        assert 'overflow-wrap:anywhere' in CSS and '-webkit-line-clamp:var(--linies-nom)' in CSS
        assert 'color:#1a1a18;font-size:14px;font-weight:600' in CSS
        assert 'font-size:12px;color:#52514e' in CSS
        esperats = {
            'igual': ('#2a78d6', '#eef4fc', '#1d5fae'),
            'aula-nova': ('#2f8f46', '#edf6ef', '#1f6b33'),
            'canvi': ('#e8820c', '#fff4e5', '#8f4c00'),
            'relaxada': ('#d03b3b', '#fdeeee', '#a12c2c'),
        }

        def llum(color):
            canals = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            return sum(p * (v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4)
                       for p, v in zip((.2126, .7152, .0722), canals))

        for clau, colors in esperats.items():
            assert ESTATS[clau][1:] == colors
            _, fons, text = colors
            assert (llum(fons) + .05) / (llum(text) + .05) >= 4.5
            assert f'background:{fons}' in CSS and f'color:{text}' in CSS

    def test_filtres_blancs_i_estat_persistent(self):
        from components.graella import CSS_FILTRES, filtres_html
        from components.prova_graella import setmana_inventada
        html = filtres_html(setmana_inventada())
        assert 'Totes (23)' in html and 'Aula assignada (1)' in html
        assert html.count('aria-pressed="true"') == 1
        assert 'background:#fff;color:#1a1a18;border:1px solid' in CSS_FILTRES
        assert 'border-color:#1a1a18;font-weight:700;outline:none' in CSS_FILTRES
        assert 'width:10px;height:10px;border-radius:3px' in CSS_FILTRES
        assert 'flex-wrap:wrap' in CSS_FILTRES
        with app_inventada() as at:
            assert at.button(key='p2-boto-totes').label.startswith('Totes (')
            at.button(key='p2-boto-aula-nova').click().run(timeout=30)
            assert at.session_state['p2-filtre'] == 'aula-nova'
            at.selectbox(key='p2-setmana').select(date(2027, 3, 15)).run(timeout=30)
            assert at.session_state['p2-filtre'] == 'aula-nova'
            assert not at.exception and not at.error

    def test_prova_comparteix_html_i_css(self):
        from components.graella import CSS, CSS_FILTRES
        from components.prova_graella import genera, setmana_inventada
        html = genera()
        assert CSS in html and CSS_FILTRES in html
        assert 'background-image:var(--linies)' in html
        assert all(f'style="width:{ample}px"' in html for ample in (1160, 900, 390))
        assert html.count(taula_html(setmana_inventada(), 'Setmana inventada', estils=False)) == 3


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
def app_inventada(sessions_extra=()):
    """Cap prova nova de pàgina depèn de les dades del repte."""
    from tempfile import TemporaryDirectory
    from streamlit.testing.v1 import AppTest
    base = crea_base()
    base.sessions['S90001'].aula = ''
    tercer = sessio('S90020', cohorts=('GXX:3r',), ini=900)
    base.sessions[tercer.id] = tercer
    sense_curs = sessio('INVENTADA-SENSE-CURS', cohorts=('GXX:?',))
    base.sessions[sense_curs.id] = sense_curs
    base.sessions.update((s.id, s) for s in sessions_extra)
    proposta = Proposta.de_base(base)
    proposta.files['S90001'].aula = 'Q9/0001'
    proposta.files['S90002'].h_ini = '10:00'
    with TemporaryDirectory(dir=ARREL.parent) as carpeta:
        arrel = Path(carpeta)
        (arrel / '5.2').mkdir()
        (arrel / '5.2' / 'proposta.csv').touch()
        with patch('pagines.part2.RESULTATS', arrel), \
             patch('pagines.part2.carrega_dades', return_value=(base, {'100001': 'Desenvolupament d’aplicacions per a Enginys Inventats'}, {'GXX': 'Grau inventat'})), \
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
        assert '<script>alert(1)</script>' not in html and '&lt;script&gt;' in html
        assert '<script>' not in html  # Les línies de fons són CSS, també en exportar.
        assert 'Dilluns' in html and 'data-minut="540"' in html
        assert '20:30–21:00' not in html


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


    def test_doble_amb_amfitrio_fora_del_grup_i_aula_de_la_proposta(self):
        from components.graella import celles
        host = sessio('HOST-INVENTAT', grup='TE/81', cohorts=('GXX:1r',))
        double = sessio('DOBLE-INVENTAT', grup='TE/91', cohorts=('GDD:3r',),
                        aula='', sense_espai=True)
        base = Base({s.id: s for s in (host, double)}, {})
        p = Proposta.de_base(base)
        p.files[host.id].aula = 'Q9/0002'
        c, = celles(base, p, host.data, cohort='GDD:3r', linia=double.linia)
        assert c.aula == '' and not c.aula_assignada and not c.canvi_aula
        for originals in (True, False):
            html = contingut_graella(taula_html([c], originals=originals))
            assert 'Amb el grup 81 · Aula Q9/0002' in html
            assert 'Pendent d’assignar aula' not in html
            assert 'Aula no indicada' not in html
        assert len(celles_aula(base, p, host.data, 'Q9/0002')) == 1

    def test_doble_per_unitat_compartida_i_sense_amfitrio(self):
        from components.graella import celles
        host = sessio('HOST-INVENTAT', compartida='UNITAT-INVENTADA')
        double = sessio('DOBLE-INVENTAT', codi='100099', grup='TE/91',
                        compartida=host.compartida, aula='', sense_espai=True)
        base = Base({s.id: s for s in (host, double)}, {})
        p = Proposta.de_base(base)
        c = next(c for c in celles(base, p, host.data) if c.id_sessio == double.id)
        assert 'Amb el grup 81 · Aula Q9/0001' in taula_html([c])
        p.files[host.id].data = '2027-03-15'
        c, = celles(base, p, host.data)
        html = taula_html([c])
        assert 'Classe compartida amb un altre grup' in html
        assert 'Pendent d’assignar aula' not in html

    def test_doble_orfe_i_aula_amfitriona_absent(self):
        from components.graella import celles
        double = sessio('DOBLE-INVENTAT', aula='', sense_espai=True)
        host = sessio('HOST-INVENTAT', grup='TE/91', aula='')
        base = Base({s.id: s for s in (host, double)}, {})
        p = Proposta.de_base(base)
        cs = celles(base, p, double.data)
        c = next(c for c in cs if c.id_sessio == double.id)
        assert c.ubicacio_compartida == 'Classe compartida amb un altre grup'
        host.codi = '100099'
        c = next(c for c in celles(base, p, double.data) if c.id_sessio == double.id)
        assert 'Classe compartida amb un altre grup' in taula_html([c])

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
            assert html.count('class="horari"') == 2  # Grup i aula, sense duplicats.
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
        graella = estructura_graella(html)
        assert sense_marques_nom(html).count('<b>Assignatura Inventada I</b>') == 1
        assert sense_marques_nom(html).count('<b>Assignatura Inventada II</b>') == 1
        assert [posicio_classe(c) for _, c in graella.classes] == [(1, 121, 1, 2), (46, 106, 2, 3)]
        assert graella.dies[0]['data-carrils'] == '2'
        assert '08:30–10:30' in html

    def test_classe_sola_aprofita_amplada_del_dia(self):
        from components.graella import Cella
        cs = [Cella('S90001', 'L', 510, 630, 'Q9/0001', 'Assignatura Inventada I', 'Teoria', '81', False, False),
              Cella('S90009', 'L', 630, 690, 'Q9/0001', 'Assignatura Inventada II', 'Problemes', '811', False, False),
              Cella('S90010', 'L', 630, 690, 'Q9/0002', 'Assignatura Inventada III', 'Problemes', '812', False, False)]
        graella = estructura_graella(taula_html(cs))
        assert [posicio_classe(c) for _, c in graella.classes] == [
            (1, 121, 1, 3), (121, 181, 1, 2), (121, 181, 2, 3)]

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
        html = contingut_graella(taula_html(dades))
        assert 'classe relaxada' in html
        assert 'Excepció de calendari' in html
        assert 'Festiu &lt;especial&gt;' in html


class TestAssignacions(unittest.TestCase):
    def test_llegenda_i_etiquetes_sense_codis(self):
        from components.graella import Cella, llegenda_html
        c = Cella('S90001', 'L', 510, 570, '', 'Assignatura Inventada I', 'Teoria', 'TE/81', False, False)
        html = contingut_graella(taula_html([c], originals=True))
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
        html = contingut_graella(taula_html(noves))
        assert 'Aula assignada' in html and 'class="classe canvi' not in html
        assert 'class="classe aula-nova"' in html
        resum = resum_grup(base, p, actuals, noves)
        assert '0 canvien d’aula' in resum and '1 amb aula assignada' in resum


class TestRedisseny(unittest.TestCase):
    def test_grup_es_reinicia_amb_curs_i_estudis_i_coincideix_amb_la_graella(self):
        extra = (
            sessio('INVENTADA-31', grup='TE/31', cohorts=('GXX:3r',), ini=900),
            sessio('INVENTADA-61', grup='TE/61', cohorts=('GXX:3r',), ini=960),
            sessio('INVENTADA-ALTRE-31', grup='TE/31', cohorts=('GYY:1r',)),
            sessio('INVENTADA-ALTRE-914', grup='TE/914', cohorts=('GYY:1r',)),
        )
        with app_inventada(extra) as at:
            def comprova_grup(numero):
                assert not at.exception and not at.error
                assert at.selectbox(key='p2-grup').value == numero
                assert at.session_state['p2-grup'] == numero
                html = '\n'.join(m.value for m in at.markdown)
                assert f'class="horari-titol">Proposta · Grup {numero} ·' in html

            at.selectbox(key='p2-curs').select('3r').run(timeout=30)
            comprova_grup('31')
            at.selectbox(key='p2-grup').select('61').run(timeout=30)
            comprova_grup('61')
            at.selectbox(key='p2-curs').select('1r').run(timeout=30)
            comprova_grup('81')
            at.selectbox(key='p2-grup').select('914').run(timeout=30)
            # 914 també és vàlid als altres estudis: igualment tria el primer.
            at.selectbox(key='p2-titulacio').select('GYY').run(timeout=30)
            comprova_grup('31')
            at.selectbox(key='p2-titulacio').select('GXX').run(timeout=30)
            at.selectbox(key='p2-curs').select('?').run(timeout=30)
            at.selectbox(key='p2-titulacio').select('GYY').run(timeout=30)
            assert at.selectbox(key='p2-curs').value == '1r'
            comprova_grup('31')

    def test_una_hora_reserva_abans_abans_del_grup_tambe_en_carrils_estrets(self):
        from components.graella import Cella, CSS, pressupost_classe
        cs = [Cella(f'INVENTADA-MOGUDA-{i}', 'J', 750, 810, 'Q9/0001',
                    'Assignatura inventada amb nom llarg', 'Problemes', f'PAUL/81{i}',
                    True, False, abans='Abans: dijous 12:30 · Q9/0002') for i in range(4)]
        html = taula_html(cs)
        p = pressupost_classe(60, nota=True)
        assert p['ubicacio'] and p['nota'] and not p['grup']
        for _, attrs in estructura_graella(html).classes:
            assert '--mostra-nota:block;' in attrs['style']
            assert '--mostra-grup:none;' in attrs['style']
        assert html.count('<small class="nota"><span class="nota-ampla">Abans: dijous 12:30</span>') == 4
        estret = CSS.split('@container p2-classe (width < 180px)', 1)[1]
        assert '.nota{display:none;}' not in estret

    def test_detalls_natius_fora_del_scroll_i_amb_tot_el_text(self):
        from html.parser import HTMLParser
        from components.graella import Cella, CSS

        class Detalls(HTMLParser):
            def __init__(self):
                super().__init__()
                self.pila, self.panells, self.botons = [], {}, []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if 'popover' in attrs:
                    assert not any('horari-scroll' in a.get('class', '').split() for a in self.pila)
                    self.panells[attrs['id']] = attrs
                if 'classe' in attrs.get('class', '').split():
                    assert tag == 'button' and attrs['aria-haspopup'] == 'dialog'
                    self.botons.append(attrs)
                if tag not in ('br', 'hr', 'meta', 'input'):
                    self.pila.append(attrs)

            def handle_endtag(self, tag):
                self.pila.pop()

        cs = [Cella(f'INVENTADA-DETALL-{i}', 'L', 510, 570, 'Q9/0001',
                    'Nom complet d’una assignatura inventada molt llarga & especial',
                    'Problemes', f'PAUL/81{i}', True, False,
                    abans='Abans: dijous 12:30 · Q9/0002') for i in range(4)]
        parser = Detalls()
        html = taula_html(cs, 'Grup inventat', estils=False) + taula_html(cs, 'Aula inventada', estils=False)
        parser.feed(html)
        assert len(parser.panells) == len(parser.botons) == 8
        assert not parser.pila
        for boto in parser.botons:
            panel = parser.panells[boto['popovertarget']]
            assert panel['popover'] == 'auto'  # Tancament natiu amb fora o Esc.
            assert panel['role'] == 'dialog'
            assert f'id="{panel["aria-labelledby"]}"' in html
            assert f'popovertarget="{panel["id"]}" popovertargetaction="hide"' in html
        assert '<h4' in html and 'Nom complet d’una assignatura inventada molt llarga &amp; especial</h4>' in html
        assert 'position:fixed;inset:12px' in CSS
        assert 'min-width:min(260px,calc(100vw - 24px))' in CSS
        assert 'max-width:calc(100vw - 24px)' in CSS
        assert '.classe[open]' not in CSS and '<details' not in html

    def test_resum_compta_aules_uniques_de_tots_els_subgrups_sense_buides(self):
        from dataclasses import replace
        from components.graella import Cella
        from pagines.part2 import resum_html
        base = crea_base()
        p = Proposta.de_base(base)
        c = Cella('S90001', 'L', 510, 570, 'Q9/0001', 'Inventada', 'Teoria', 'TE/81', False, False)
        cs = [c, replace(c, id_sessio='S90002', aula='Q9/0002', grup='PAUL/811'),
              replace(c, id_sessio='S90003', aula='Q9/0003', grup='SEM/813'),
              replace(c, id_sessio='S90004', aula='Q9/0004'),
              replace(c, id_sessio='S90005', aula='Q9/0001'),
              replace(c, id_sessio='S90006', aula='')]
        assert '<b>4</b><span>aules a la setmana</span>' in resum_html(base, p, cs, cs, True)

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
        from components.graella import Cella, CSS
        a = Cella('S90001', 'L', 510, 570, '', 'Inventada', 'Teoria', '81', False, False)
        cs = [a, replace(a, id_sessio='S90002', ini=600, fi=660),
              replace(a, id_sessio='S90003', ini=600, fi=660)]
        cs += [replace(a, id_sessio=f'S9001{i}', dia=dia) for i, dia in enumerate('MXJV')]
        html = taula_html(cs)
        graella = estructura_graella(html)
        assert [d['data-carrils'] for d in graella.dies] == ['2', '1', '1', '1', '1']
        assert 'grid-template-columns:56px minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)' in html
        assert '--ample-mobil:888px' in html
        assert [posicio_classe(c)[3] - posicio_classe(c)[2] for _, c in graella.classes] == [2, 1, 1, 1, 1, 1, 1]
        assert 'container:p2-graella / inline-size' in CSS
        assert 'overflow-x:auto' in CSS and 'position:sticky;left:0' in CSS

    def test_classes_consecutives_no_obren_carrils_per_arrodoniment(self):
        from dataclasses import replace
        from components.graella import Cella
        a = Cella('S90001', 'L', 510, 555, '', 'Inventada I', 'Teoria', '81', False, False)
        b = replace(a, id_sessio='S90002', ini=555, fi=615, assignatura='Inventada II')
        html = taula_html([a, b])
        graella = estructura_graella(html)
        assert '--ample-mobil:498px' in html
        assert graella.dies[0]['data-carrils'] == '1'
        assert '09:15–10:15' in html
        assert len(graella.classes) == 2
        assert [posicio_classe(c) for _, c in graella.classes] == [(1, 46, 1, 2), (46, 106, 1, 2)]
        html = taula_html([a, replace(b, ini=554)])
        assert '--ample-mobil:888px' in html
        assert estructura_graella(html).dies[0]['data-carrils'] == '2'

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
        assert ESTATS['igual'][1:] == ('#2a78d6', '#eef4fc', '#1d5fae')
        assert 'border-left' not in CSS
        assert 'border:0;border-radius:10px;padding:8px 10px' in CSS
        assert 'background:#edf6ef' in CSS and 'background:#fdeeee' in CSS
        assert 'background:#fff4e5' in CSS and 'background:#eef4fc' in CSS
        for cella, esperat in casos:
            html = taula_html([cella])
            nom = ESTATS[esperat][0]
            assert f'title="{nom} ·' in html and f'aria-label="{nom} ·' in html
            assert '<span class="estat">' not in html and '<svg' not in html

    def test_pressupost_classes_curtes_i_noms_llargs(self):
        from components.graella import Cella, CSS, pressupost_classe
        nom = 'Assignatura inventada amb un nom molt llarg & difícil "de resumir" ' * 8
        for durada in (30, 45, 60, 90, 120, 180):
            for carrils in range(1, 5):
                cs = [Cella(f'CURTA-{i}', 'L', 510, 510 + durada,
                            'Aula inventada molt llarga', nom, 'Problemes',
                            f'PAUL/99{i}', True, False) for i in range(carrils)]
                html = taula_html(cs)
                graella = estructura_graella(html)
                assert graella.dies[0]['data-carrils'] == str(carrils)
                for _, attrs in graella.classes:
                    assert nom in attrs['title'] and nom in attrs['aria-label']
                    for nota in (False, True):
                        p = pressupost_classe(durada, nota=nota)
                        # Recalculem l'alçada amb les mètriques reals del CSS.
                        secundaries = sum(p[k] for k in ('ubicacio', 'grup', 'nota'))
                        visible = 2 * p['padding'] + p['nom'] * 17.5 + secundaries * (16.2 + 3)
                        assert visible <= durada * 1.6 - 6
                        assert abs(visible - p['visible']) < 1e-6
                        assert p['nom'] >= 1 and p['ubicacio']
                        assert not p['nota'] or p['ubicacio']
                        if durada >= 60 and nota:
                            assert p['nota']
                        if nota:
                            assert f'--linies-nom:{p["nom"]};' in attrs['style']
                            for camp in ('ubicacio', 'grup', 'nota'):
                                assert f'--mostra-{camp}:{"block" if p[camp] else "none"};' in attrs['style']
                if durada == 30:
                    assert pressupost_classe(durada)['padding'] == 2
                    assert not pressupost_classe(durada, nota=True)['grup']
        assert '-webkit-line-clamp:var(--linies-nom)' in CSS
        assert '.classe{overflow:hidden;}' in CSS
        assert '.classe[open]' not in CSS

    def test_tres_linies_i_nota_curta_amb_detall_complet(self):
        from dataclasses import replace
        from components.graella import Cella
        c = Cella('INVENTADA-NOTA', 'L', 510, 630, 'Aula inventada',
                  'Assignatura Inventada', 'Problemes', 'PAUL/999', True, False,
                  abans='Abans: dijous 12:30 · Aula anterior inventada (08/03/2027)')
        html = taula_html([c])
        assert '<b>Assignatura Inventada</b><small class="ubicacio">' in sense_marques_nom(html)
        assert '<span class="hora-inici">08:30</span><span class="hora-separador">–</span><span class="hora-fi">10:30</span>' in html
        assert '<span class="aula-classe"> · Aula inventada</span></small><small>Problemes · Subgrup 999</small>' in html
        assert '<small class="nota"><span class="nota-ampla">Abans: dijous 12:30</span>' in html
        assert 'Aula anterior inventada' in html
        igual = taula_html([replace(c, canvi_franja=False)])
        assignada = taula_html([replace(c, canvi_franja=False, aula_assignada=True)])
        assert '<small class="nota">' not in igual and '<small class="nota">' not in assignada
        motiu = 'Motiu inventat amb <etiqueta> i prou paraules per comprovar que el resum és curt i el detall es conserva sencer.'
        especial = taula_html([replace(c, relaxacions=(motiu,))])
        assert '<small class="nota"><span class="nota-ampla">Abans: dijous 12:30</span>' in especial
        assert 'Motiu inventat amb &lt;etiqueta&gt;' in especial  # Motiu complet al detall.
        assert motiu.replace('<', '&lt;').replace('>', '&gt;') in especial
        assert '<etiqueta>' not in especial

    def test_filtre_apaga_sense_amagar_ni_recolocar(self):
        from dataclasses import replace
        from components.graella import Cella, recomptes_estat
        a = Cella('S90001', 'L', 510, 570, '', 'Inventada I', 'Teoria', '81', False, False)
        b = replace(a, id_sessio='S90002', ini=570, fi=630, aula='Q9/0001', aula_assignada=True)
        html = contingut_graella(taula_html([a, b], filtre='aula-nova'))
        assert 'class="classe igual apagada" data-estat="igual"' in html
        assert 'class="classe aula-nova" data-estat="aula-nova"' in html
        assert len(estructura_graella(html).classes) == 2
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
            html = contingut_graella(html)
            assert len(estructura_graella(html).classes) == 1
            assert 'Inventada I / Inventada II' in html
            assert 'Classe compartida' in html
        assert recomptes_estat(aula) == {'igual': 1}
        p.files['S90002'].aula = 'Q9/0002'
        assert len(estructura_graella(taula_html(celles_grup(base, p, date(2027, 3, 8), 'GXX', '1r', '81'))).classes) == 2
        p.files['S90002'].aula = 'Q9/0001'
        p.files['S90002'].h_ini = '09:30'
        assert len(estructura_graella(taula_html(celles_aula(base, p, date(2027, 3, 8), 'Q9/0001'))).classes) == 2

    def test_noms_grups_i_amplada_per_carril(self):
        from components.graella import Cella, CSS, nom_grup
        assert nom_grup('TE/912', 'Teoria') == 'Grup 912 · teoria'
        assert nom_grup('PAUL/903', 'Problemes') == 'Subgrup 903 · problemes'
        assert nom_grup('SEM/906', 'Seminari') == 'Subgrup 906 · seminari'
        cs = [Cella(f'S90{i:03}', 'L', 510, 570, '', 'Assignatura Inventada', 'Problemes', f'PAUL/904{i}', False, False) for i in range(4)]
        html = contingut_graella(taula_html(cs))
        assert '--ample-mobil:1668px' in html  # Mínim mòbil per a cinc dies iguals.
        assert sum(int(d['data-carrils']) for d in estructura_graella(html).dies) == 8
        assert 'min-width:0;min-height:0' in CSS and 'overflow:auto' not in CSS
        assert 'overflow-wrap:anywhere' in CSS and 'word-break:normal' in CSS
        assert 'PAUL/' not in html

    def test_torn_unic_i_detall_accessible(self):
        base = Base({'S90001': sessio('S90001', ini=900)}, {})
        p = Proposta.de_base(base)
        p.files['S90001'] = Assignacio('M', '16:00', 'Q9/0002')
        c, = celles_grup(base, p, date(2027, 3, 8), 'GXX', '1r', '81')
        html = contingut_graella(taula_html([c]))
        assert [int(h['data-minut']) for h in estructura_graella(html).hores] == list(range(510, 1261, 30))
        assert 'Abans: dilluns 15:00' in html
        assert 'aria-haspopup="dialog"' in html and 'title="Canvia ·' in html

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
    focus(){this.focused++;}, scrollIntoView(){},
    matches(s){return s===':popover-open'&&this.popoverShown;},
    showPopover(){this.popoverShown=true;this.offsetParent=null;}};
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
  assert.equal(launcher.attrs.popover,'manual');
  assert.ok(launcher.popoverShown);
  assert.equal(Number.parseFloat(launcher.style.left),18);
  assert.equal(Number.parseFloat(launcher.style.top),582);
  assert.equal(panel.attrs.role,'dialog');
  assert.equal(panel.focused,i+1);
  assert.equal(Number.parseFloat(panel.style.left)+parentRect.left,512);
  targets[i].rect.right=540;
  doc.dispatch('scroll');
  assert.equal(Number.parseFloat(panel.style.left)+parentRect.left,552);
  assert.equal(doc.listeners.keydown.size,1);
  assert.equal(host.listeners.resize.size,2);
}
// Canvi d'origen amb el menú obert/plegat: el popover conserva coordenades de viewport.
parentRect.left=280;host.dispatch('resize');
assert.equal(Number.parseFloat(launcher.style.left),18);
parentRect.left=20;
host.innerWidth=390;
host.dispatch('resize');
assert.equal(Number.parseFloat(launcher.style.left),18);
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
        # La secció «Ajuda» («Pregunta-ho · aviat») ja no hi és: l'assistent és el botó de baix a la dreta.
        assert [n.value for n in crida.args[0].keys] == ['Com està l’horari', 'La proposta']
        pagines = [n for n in ast.walk(crida) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'Page']
        titols = [next(k.value.value for k in n.keywords if k.arg == 'title') for n in pagines]
        assert 'Horari proposat' in titols
        assert [k.value.value for n in pagines for k in n.keywords if k.arg == 'url_path'] == ['avui', 'respostes', 'part2', 'junta', 'imprevistos']


def test_setmana_densa_cap_en_escriptori_i_dies_iguals():
    from components.graella import CSS
    from components.prova_graella import setmana_carrils_inventada
    for carrils in ((2, 2, 1, 3, 2), (4, 3, 3, 3, 3), (4, 4, 4, 4, 4)):
        html = taula_html(setmana_carrils_inventada(carrils), estils=False)
        assert [int(d['data-carrils']) for d in estructura_graella(html).dies] == list(carrils)
        assert 'grid-template-columns:56px ' + ' '.join(['minmax(0, 1fr)'] * 5) in html
        assert 'min-width:' not in html  # Cap mínim inline que forci scroll a escriptori.
    assert '.horari{min-width:0px;' in CSS
    assert '@media (width < 700px)' in CSS
    assert '@container p2-graella (width < 900px)' not in CSS
    assert 'min-width:var(--ample-mobil)' in CSS
    assert 'container:p2-classe / inline-size' in CSS
    assert '@container p2-classe (width < 180px)' in CSS


def test_xat_obert_anulla_minim_mobil_nomes_a_partir_de_700px():
    import re
    from dataclasses import replace
    from components.graella import Cella
    c = Cella('INVENTADA-XAT', 'X', 870, 930, 'Q9/0001', 'Nom inventat',
              'Problemes', 'PAUL/811', False, False)
    html = taula_html([c, replace(c, id_sessio='INVENTADA-XAT-2')])
    css = html.split('<style>', 1)[1].split('</style>', 1)[0]
    mobil = re.search(r'@media \(width < 700px\)\{\s*([^}]+})\s*}', css)[1]
    assert '.horari{min-width:var(--ample-mobil);}' in mobil
    xat = re.search(r'@media \(min-width:700px\)\{(.*?)\n}', css, re.S)[1]
    assert 'html.xatia-obert .p2-horari .horari{min-width:0;' in xat
    assert css.index('@media (min-width:700px)') > css.index('@media (width < 700px)')
    assert 'column-gap:4px;padding-inline:8px;' in xat
    assert '.dia-horari{column-gap:2px;}' in xat
    assert '.classe{padding-inline:2px;}' in xat
    assert '--ample-mobil:888px' in html
    assert 'grid-template-columns:repeat(2,minmax(0,1fr))' in html
    # A 470px, dos carrils encara admeten HH:MM a 11px sense el·lipsi.
    carril = ((470 - 2 * 8 - 56 - 5 * 4) / 5 - 2) / 2
    assert carril - 2 * 2 >= 32


def test_dies_iguals_amb_tres_carrils_i_contenidors_descriptori_estrets():
    import re
    from dataclasses import replace
    from components.graella import Cella, DIES
    c = Cella('INVENTADA-DIES-IGUALS', 'X', 870, 930, 'Q9/0001',
              'Nom inventat llarg', 'Problemes', 'PAUL/811', True, False,
              abans='Abans: dimecres 11:30 · Q9/0002')
    cs = [replace(c, id_sessio=f'INVENTADA-CARRIL-{i}') for i in range(3)]
    cs += [replace(c, dia=dia, id_sessio=f'INVENTADA-DIA-{dia}') for dia in DIES if dia != 'X']
    html = taula_html(cs)
    assert [int(d['data-carrils']) for d in estructura_graella(html).dies] == [1, 1, 3, 1, 1]
    # Els set carrils no alteren els cinc pesos dels dies.
    columnes = re.search(r'class="horari" style="[^"]*grid-template-columns:([^;]+);', html)[1]
    assert columnes == '56px ' + ' '.join(['minmax(0, 1fr)'] * 5)
    css = html.split('<style>', 1)[1].split('</style>', 1)[0]
    # Cap regla de contenidor imposa un mínim pel simple fet de fer <900px.
    minims = re.findall(r'([^{}]+)\{([^{}]*min-width:var\(--ample-mobil\)[^{}]*)}', css)
    assert len(minims) == 1
    mobil = re.search(r'@media \(width < 700px\)\{(.*?)\n}', css, re.S)[1]
    assert minims[0][1] in mobil
    # Amb el xat (575px), les caselles de dimecres fan uns 31px;
    # sense el xat (887px), uns 46px. En ambdós casos s'activa el compacte.
    for ample, padding, separacio, gap in ((575, 8, 4, 2), (887, 16, 10, 6)):
        dia = (ample - 2 * padding - 56 - 5 * separacio) / 5
        contingut = (dia - 2 * gap) / 3 - 2 * 2
        assert 26 <= contingut < 180
        assert (contingut < 32) == (ample == 575)


def test_padding_i_hora_de_10px_per_carrils_de_30_a_45px():
    import re
    from components.graella import Cella, nom_assignatura_html
    c = Cella('INVENTADA-MOLT-ESTRETA', 'X', 870, 930, 'Q9/0001',
              'Electromagnetisme inventat', 'Problemes', 'PAUL/811',
              True, False, abans='Abans: dimecres 11:30 · Q9/0002')
    html = taula_html([c])
    css = html.split('<style>', 1)[1].split('</style>', 1)[0]
    assert 'padding-block:var(--padding-classe,8px);padding-inline:2px;' in css
    compacte = re.search(r'@container p2-classe \(width < 180px\)\{(.*?)\n}', css, re.S)[1]
    assert '.resum-classe{padding-inline:0;}' in compacte
    curt = re.search(r'@container p2-classe \(width < 60px\)\{(.*?)\n}', css, re.S)[1]
    assert '.abans-etiqueta{display:block;white-space:nowrap;}' in curt
    petit = re.search(r'@container p2-classe \(width < 32px\)\{(.*?)\n}', css, re.S)[1]
    assert '.hora-inici,.p2-horari .classe .hora-fi,.p2-horari .classe .abans-hora{font-size:10px;letter-spacing:-.5px;}' in petit
    assert '.abans-etiqueta{font-size:10px;letter-spacing:-1px;}' in petit
    assert '>dc<span class="abans-hora">11:30</span>' in html
    assert '<b>' + nom_assignatura_html(c.assignatura) + '</b>' in html
    assert '--mostra-nom-estret:-webkit-box;' in html
    assert '--mostra-nota-estret:block;' in html
    assert 'overflow:hidden;text-overflow:ellipsis' in css
    assert 'max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis' in css


def test_hores_i_abans_compactes_sencers_en_classes_simultanies_duna_hora():
    import re
    from dataclasses import replace
    from components.graella import Cella, pressupost_classe
    c = Cella('INVENTADA-COMPACTA', 'X', 870, 930, 'Q9/0001',
              'Nom inventat que es pot abreujar', 'Problemes', 'PAUL/811',
              True, False, abans='Abans: dimecres 10:30 · Q9/0002')
    html = taula_html([c, replace(c, id_sessio='INVENTADA-COMPACTA-2')])
    css = html.split('<style>', 1)[1].split('</style>', 1)[0]
    estret = re.search(r'@container p2-classe \(width < 180px\)\{(.*?)\n}', css, re.S)[1]
    assert '.hora-inici,.p2-horari .classe .hora-fi{display:block;}' in estret
    assert 'font-size:11px;line-height:12px;white-space:nowrap;overflow:visible;text-overflow:clip' in estret
    assert '.hora-separador,.p2-horari .classe .aula-classe{display:none;}' in estret
    assert '.resum-classe>small:not([class]){display:none;}' in estret
    assert '.nota-ampla{display:none;}' in estret
    assert '.nota-compacta,.p2-horari .classe .abans-hora{display:block;}' in estret
    assert '.abans-hora{white-space:nowrap;' in estret
    assert html.count('<span class="hora-inici">14:30</span>') == 2
    assert html.count('<span class="hora-fi">15:30</span>') == 2
    assert html.count('aria-hidden="true"><span class="abans-etiqueta">Abans </span>dc<span class="abans-hora">10:30</span>') == 2
    assert 'Abans: dimecres 10:30 · Q9/0002' in html  # Detall complet.
    for _, attrs in estructura_graella(html).classes:
        assert '--mostra-nota-estret:block;' in attrs['style']
        assert '--linies-nom-estret:1;' in attrs['style']
    for durada in (30, 45, 60, 90, 120):
        for nota in (False, True):
            p = pressupost_classe(durada, nota=nota, estret=True)
            # Dues línies de 12px per a l’interval i tres per a Abans/dia/hora.
            files = 1 + bool(p['nom']) + p['nota']
            visible = (2 * p['padding'] + 24 + p['nom'] * 17.5
                       + p['nota'] * 36 + (files - 1) * 3)
            assert visible == p['visible'] <= durada * 1.6 - 6
            assert p['ubicacio'] and not p['grup']
            if durada >= 60:
                assert p['nom'] >= 1 and p['nota'] == nota
    # Una nota secundària cedeix espai al nom; «Abans» conserva la prioritat.
    especial = taula_html([replace(c, canvi_franja=False, abans='', relaxacions=('Nota inventada',))])
    assert '--mostra-nota-estret:none;' in especial


def test_abans_visible_en_tres_linies_dins_duna_hora_en_carrils_estrets():
    import re
    from components.graella import Cella, pressupost_classe
    c = Cella('INVENTADA-ABANS-VISIBLE', 'X', 870, 930, 'Q9/0001',
              'Assignatura inventada amb un nom llarg', 'Problemes', 'PAUL/811',
              True, False, abans='Abans: dimecres 11:30 · Q9/0002')
    html = taula_html([c])
    css = html.split('<style>', 1)[1].split('</style>', 1)[0]
    estret = re.search(r'@container p2-classe \(width < 60px\)\{(.*?)\n}', css, re.S)[1]
    assert '.abans-etiqueta{display:block;white-space:nowrap;}' in estret
    assert not re.search(r'\.abans-etiqueta\{[^}]*display:none', css)
    assert '<span class="abans-etiqueta">Abans </span>dc<span class="abans-hora">11:30</span>' in html
    _, attrs = estructura_graella(html).classes[0]
    assert '--mostra-nota-estret:block;' in attrs['style']
    assert '--mostra-nom-estret:-webkit-box;' in attrs['style']
    assert '--linies-nom-estret:1;' in attrs['style']
    p = pressupost_classe(60, nota=True, estret=True)
    assert p['nota'] and p['ubicacio'] and not p['grup'] and p['nom'] == 1
    # Nom: 17.5px; interval: 2 × 12px; Abans/dia/hora: 3 × 12px;
    # dos gaps de 3px i dos paddings de 2px: 87.5px dins els 90px útils.
    alçada = 17.5 + 2 * 12 + 3 * 12 + 2 * 3 + 2 * 2
    assert p['visible'] == alçada == 87.5
    assert alçada <= p['caixa'] == 60 * 1.6 - 6 == 90


def test_paraules_noms_atomiques_amb_abreviacio_marcada():
    import re
    from html import unescape
    from components.graella import CSS, nom_assignatura_html
    from components.prova_graella import setmana_carrils_inventada
    noms = ('Organització i Gestió', 'Probabilitat i Processos',
            'Electromagnetisme interdisciplinari', "Desenvolupament d’aplicacions")
    for nom in noms:
        markup = nom_assignatura_html(nom)
        paraules = re.findall(r'<span class="nom-paraula">(.*?)</span>', markup)
        # Cap fragment sense marca: cada unitat conté una paraula sencera.
        assert [unescape(p) for p in paraules] == nom.split()
    for carrils in ((3, 3, 3, 3, 3), (4, 3, 3, 3, 3)):
        classes = setmana_carrils_inventada(carrils)
        html = taula_html(classes, estils=False)
        for c in classes:
            assert nom_assignatura_html(c.assignatura) in html
            assert c.assignatura in unescape(html)  # title i aria-label complets.
    for selector, regla in re.findall(r'([^{}]+)\{([^{}]*)\}', CSS):
        if '.classe' in selector and (' b' in selector or '.nom-paraula' in selector):
            assert 'word-break:break-all' not in regla
            assert 'overflow-wrap:anywhere' not in regla
    regla = re.search(r'\.nom-paraula\{([^}]*)}', CSS)[1]
    assert 'white-space:nowrap' in regla and 'display:inline-block' in regla
    assert 'max-width:100%' in regla
    assert 'overflow:hidden' in regla and 'text-overflow:ellipsis' in regla
    assert '.detall-classe h4' in CSS and '.classe[open]' not in CSS

from datetime import date
from pathlib import Path
import sys

ARREL = Path(__file__).resolve().parent
sys.path.insert(0, str(ARREL.parent))
sys.path.insert(0, str(ARREL))

import unittest
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
    valors = dict(id=sid, codi='123', tipus=tipus, grup=grup, data=data,
        dia='L', ini=510, durada=60, alumnes=20, aula='Q9/5004',
        cohorts=('GED:1r',), torn='mati', fixada='', docents=frozenset())
    valors.update(kwargs)
    return Sessio(**valors)


def crea_base():
    sessions = [sessio('T'), sessio('P', 'PAUL', 'PAUL/811'),
        sessio('S', 'SEM', 'SEM/907'), sessio('altre', grup='TE/915'),
        sessio('lab', 'PLAB', 'PLAB/905'),
        sessio('setmana2', data=date(2027, 3, 15))]
    return Base({s.id: s for s in sessions}, {})


class TestGraella(unittest.TestCase):
    def test_grup_i_linies(self):
        base = crea_base()
        p = Proposta.de_base(base)
        assert grups(base)['GED']['1r']['81'] == '81'
        assert {c.id_sessio for c in celles_grup(base, p, date(2027, 3, 10), 'GED', '1r', '81')} == {'T', 'P', 'S'}


    def test_aula_canvis_i_relaxacio(self):
        base = crea_base()
        p = Proposta.de_base(base)
        p.files['T'] = Assignacio('M', '09:15', 'Q9/5009')
        c, = celles_aula(base, p, date(2027, 3, 8), 'Q9/5009', relaxacions={'T': ['Motiu declarat']})
        assert c.canvi_franja and c.canvi_aula and c.ini == 555 and c.fi == 615
        assert c.relaxacions == ('Motiu declarat',)
        assert 'Motiu declarat' in taula_html([c])
        assert '09:15–10:15' in taula_html([c])
        assert len(FRANGES) == 25 and FRANGES[-1] == 1230


    def test_recuperacio_canvia_setmana(self):
        base = crea_base()
        p = Proposta.de_base(base)
        p.files['T'] = Assignacio('V', '10:30', 'Q9/5009', '2027-03-19')
        assert not celles_aula(base, p, date(2027, 3, 8), 'Q9/5009')
        assert celles_aula(base, p, date(2027, 3, 15), 'Q9/5009')[0].canvi_franja


    def test_html_autonom_i_escapat(self):
        base = crea_base()
        p = Proposta.de_base(base)
        html = exporta_aula_html(base, p, date(2027, 3, 8), 'Q9/5004', noms={'123': '<script>alert(1)</script>'})
        assert '<!doctype html>' in html and '<style>' in html and 'lang="ca"' in html
        assert '<script>' not in html and '&lt;script&gt;' in html
        assert 'Dilluns' in html and '20:30–21:00' in html


    def test_incompleta_i_dia_incorrecte(self):
        base = crea_base()
        p = Proposta.de_base(base)
        del p.files['T']
        with raises(ValueError, match='absents'):
            celles_aula(base, p, date(2027, 3, 8), 'Q9/5004')
        p = Proposta.de_base(base)
        p.files['T'].dia = 'Z'
        with raises(ValueError, match='Dia incorrecte'):
            celles_aula(base, p, date(2027, 3, 8), 'Q9/5004')


    def test_tipica_mediana_i_desempat(self):
        base = crea_base()
        assert setmana_tipica(base) == date(2027, 3, 8)


    def test_pagina_sense_errors(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_string('from pagines.part2 import mostra\nmostra()').run(timeout=30)
        assert not at.exception
        assert not at.error
        assert any(s.label == 'Grup de teoria' for s in at.selectbox)
        at.selectbox(key='p2-setmana').select(date(2027, 3, 15)).run(timeout=30)
        assert not at.exception and not at.error

class TestMillores(unittest.TestCase):
    def test_bloc_unic_dues_hores_i_solapament(self):
        from components.graella import Cella
        a = Cella('A', 'L', 510, 630, 'Q9/5004', 'Assignatura única', 'Teoria', '81', False, False)
        b = Cella('B', 'L', 555, 615, 'Q9/5009', 'Subgrup paral·lel', 'Problemes', '811', False, False)
        html = taula_html([a, b])
        assert html.count('Assignatura única') == 1
        assert html.count('Subgrup paral·lel') == 1
        assert 'rowspan="4"' in html
        assert 'colspan="2">Dilluns' in html
        assert '08:30–10:30' in html

    def test_proposta_defecte(self):
        from pagines.part2 import proposta_per_defecte, RESULTATS
        assert str(RESULTATS) == '/Users/bernatroca/Bernat/Hackathon/resultats/nivell2'
        assert proposta_per_defecte(['Avui', '5.1', '5.2', '5.4']) == '5.2'
        assert proposta_per_defecte(['Avui', '5.1']) == '5.1'
        assert proposta_per_defecte(['Avui', '5.4']) == 'Avui'

    def test_resum_grup(self):
        from components.graella import resum_grup
        base = crea_base()
        avui = Proposta.de_base(base)
        p = Proposta.de_base(base)
        p.files['T'] = Assignacio('M', '15:00', 'Q9/5009')
        p.files['P'] = Assignacio('L', '08:30', 'Q9/5009')
        args = (date(2027, 3, 8), 'GED', '1r', '81')
        actuals = celles_grup(base, avui, *args)
        noves = celles_grup(base, p, *args)
        resum = resum_grup(base, p, actuals, noves)
        assert '1 classes canvien de dia o d’hora' in resum
        assert '2 canvien d’aula' in resum
        assert '1 canvien de torn' in resum
        assert '1 avui → 2 a la proposta' in resum
        p.files['T'].data = '2027-03-19'
        assert '1 classes canvien de dia o d’hora' in resum_grup(base, p, actuals, celles_grup(base, p, *args))

    def test_excepcio_calendari_escapada(self):
        from tempfile import TemporaryDirectory
        from pagines.part2 import carrega_excepcions
        with TemporaryDirectory(dir=ARREL.parent) as carpeta:
            path = Path(carpeta) / 'excepcions.csv'
            path.write_text('id_sessio,data,minut_inici,motiu\nT,2027-03-08,510,Festiu <especial>\n')
            motius = carrega_excepcions(str(path), 1)
        base = crea_base()
        dades = celles_grup(base, Proposta.de_base(base), date(2027, 3, 8), 'GED', '1r', '81', relaxacions=motius)
        html = taula_html(dades)
        assert 'classe relaxada' in html
        assert 'title="Excepció de calendari' in html
        assert 'Festiu &lt;especial&gt;' in html


class TestAssignacions(unittest.TestCase):
    def test_aula_assignada_neutra(self):
        from components.graella import resum_grup
        base = crea_base()
        base.sessions['T'].aula = ''
        base.sessions['P'].aula = 'J/001'
        base.sessions['S'].sense_espai = True
        avui = Proposta.de_base(base)
        p = Proposta.de_base(base)
        for sid in ('T', 'P', 'S'):
            p.files[sid].aula = 'Q9/5009'
        args = (date(2027, 3, 8), 'GED', '1r', '81')
        actuals = celles_grup(base, avui, *args)
        noves = celles_grup(base, p, *args)
        assert sum(c.canvi for c in noves) == 0
        assert sum(c.aula_assignada for c in noves) == 1
        html = taula_html(noves)
        assert 'Aula assignada.' in html and 'class="classe canvi' not in html
        resum = resum_grup(base, p, actuals, noves)
        assert '0 canvien d’aula' in resum and '1 amb aula assignada' in resum

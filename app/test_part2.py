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

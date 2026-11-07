"""Proves amb dades reals, sense servidor: python app/test_app.py."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest

ARREL = Path(__file__).resolve().parent
sys.path.insert(0,str(ARREL.parent))
sys.path.insert(0,str(ARREL))
from nivell1.troballes import PORTADA, una
from components.grafics import grafics
from presentacio import context
from servei import AULES_DISPONIBLES, AULES_RESERVA, inventari


class TestApp(unittest.TestCase):
    def carrega(self):
        return AppTest.from_file(str(ARREL/'app.py')).run(timeout=90)

    def comprova(self,app):
        self.assertEqual(list(app.exception),[])
        self.assertEqual(list(app.error),[])
        self.assertEqual(list(app.warning),[])

    def test_portada_real(self):
        app = self.carrega()
        self.comprova(app)
        self.assertTrue(any(t.value == 'Espais de l’Escola' for t in app.title))
        self.assertTrue(any(t.value == 'Com estem avui' for t in app.title))
        self.assertTrue(any(t.value == 'Sí, però just.' for t in app.subheader))
        self.assertEqual(len([m for m in app.markdown if 'class="xifra-targeta"' in m.value]),len(PORTADA)-1)
        self.assertEqual(len([b for b in app.button if b.label == 'Com ho sabem →']),len(PORTADA))
        self.assertEqual(len(app.get('plotly_chart')),0)
        self.assertFalse(any('MOSTRA' in m.value for m in app.markdown))
        self.assertEqual(app.selectbox[0].value,2)
        self.assertFalse(next(e for e in app.expander if e.label == 'Opcions').proto.expanded)
        for id_ in PORTADA:
            app.button(key='obre-'+id_).click().run(timeout=90)
            self.comprova(app)
            self.assertTrue(any(s.value == 'Què vol dir' for s in app.subheader))
            self.assertTrue(any(s.value == 'Com ho hem calculat' for s in app.subheader))
            self.assertTrue(any(s.language == 'sql' for s in app.code))
            self.assertFalse(next(e for e in app.expander if e.label.startswith('Per a tècnics')).proto.expanded)
            self.assertEqual(len(app.get('plotly_chart')),1)
            app.button(key='torna').click().run(timeout=90)

    def test_totes_les_respostes_i_detalls(self):
        app = AppTest.from_string('''
import streamlit as st
from servei import totes, versio_registre
from pagines import preguntes
st.session_state.semestre = 2
st.session_state.setmana = None
st.session_state.versio = versio_registre()
st.session_state.resultats = {t.id:t for t in totes(2,None,st.session_state.versio)}
preguntes.mostra()
''').run(timeout=90)
        self.comprova(app)
        ids = list(app.session_state.resultats)
        self.assertEqual(len(ids),11)
        self.assertEqual(len([b for b in app.button if b.label == 'Com ho sabem →']),len(ids))
        for id_ in ids:
            app.button(key='obre-'+id_).click().run(timeout=90)
            self.comprova(app)
            self.assertTrue(any(s.language == 'sql' for s in app.code))
            self.assertLessEqual(len(app.get('plotly_chart')),1)
            if id_ == 'ocupacio':
                html = '\n'.join(m.value for m in app.markdown)
                sales = inventari()
                sales = sales[sales.tipus == 'Aules docents']
                self.assertEqual(html.count('class="rajola"'),len(sales))
                self.assertIn('title="Q',html)
            app.button(key='torna').click().run(timeout=90)

    def test_grafic_mati_i_xifres(self):
        t = una('hi-cap-mati')
        with patch('components.grafics.st.plotly_chart') as mostra:
            grafics(t)
        fig = mostra.call_args.args[0]
        self.assertEqual(len(fig.data),1)
        self.assertEqual(fig.data[0].type,'bar')
        self.assertEqual(len(fig.data[0].x),5)
        self.assertEqual(list(fig.data[0].y),list(t.extra['pic'].groupby('dia',sort=False).classes.max()))
        self.assertEqual(fig.layout.shapes[0].y0,AULES_DISPONIBLES)
        self.assertEqual(fig.layout.shapes[0].line.dash,'dash')
        self.assertFalse(fig.layout.showlegend)
        c = context(t)
        self.assertEqual(c['pic_n'],int(t.extra['pic'].classes.max()))
        self.assertEqual(AULES_DISPONIBLES+AULES_RESERVA,len(inventari().query("tipus == 'Aules docents'")))

    def test_canvi_semestre(self):
        app = self.carrega()
        app.selectbox[0].select(1).run(timeout=90)
        self.comprova(app)
        self.assertEqual(len([b for b in app.button if b.label == 'Com ho sabem →']),len(PORTADA))
        app.selectbox[1].select_index(1).run(timeout=90)
        self.comprova(app)


if __name__ == '__main__':
    unittest.main()

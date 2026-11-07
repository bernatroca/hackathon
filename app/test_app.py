"""Proves locals sense servidor: executar amb python app/test_app.py."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest

ARREL = Path(__file__).resolve().parent
sys.path.insert(0, str(ARREL.parent))
sys.path.insert(0, str(ARREL))
from mostra import exemples
from nivell1.troballes import PORTADA


class TestApp(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def carrega(self):
        return AppTest.from_file(str(ARREL / 'app.py')).run(timeout=30)

    def test_portada(self):
        app = self.carrega()
        self.assertEqual(list(app.exception), [])
        self.assertEqual(list(app.error), [])
        self.assertEqual(list(app.warning), [])
        self.assertFalse(any('MOSTRA' in c.value for c in app.caption))
        self.assertEqual(len(app.get('plotly_chart')), 0)
        self.assertTrue(any('tot el semestre' in c.value and 'setmana' in c.value for c in app.caption))
        self.assertEqual(len([m for m in app.markdown if 'class="xifra-targeta"' in m.value]), 5)
        self.assertEqual(len([b for b in app.button if b.label == 'Obre la troballa']), 5)
        self.assertEqual(app.selectbox[0].value, 2)
        self.assertIsNone(app.selectbox[1].value)
        for id_ in PORTADA:
            app.button(key='obre-' + id_).click().run(timeout=30)
            self.assertEqual(list(app.exception), [])
            self.assertEqual(list(app.warning), [])
            self.assertEqual(len(app.metric), 1)
            self.assertTrue(any(s.language == 'sql' for s in app.code))
            self.assertTrue(any('Com s’ha calculat' == s.value for s in app.subheader))
            if id_ in ('ocupacio', 'hi-cap-mati'):
                self.assertEqual(len(app.get('plotly_chart')), 2)
            next(b for b in app.button if b.label == '← Torna a les troballes').click().run(timeout=30)
        app.selectbox[0].select(1).run(timeout=30)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(len([m for m in app.markdown if 'class="xifra-targeta"' in m.value]), 5)
        if len(app.selectbox[1].options) > 1:
            app.selectbox[1].select_index(1).run(timeout=30)
            self.assertEqual(list(app.exception), [])
            self.assertEqual(list(app.error), [])

    def test_resultat_real_substitueix_mostra(self):
        real = exemples()['aforament']
        real.extra = {}
        real.frase = 'Resultat del registre de prova'

        def una(id_, semestre, setmana):
            if id_ == real.id:
                return real
            raise KeyError(id_)

        with patch('nivell1.troballes.una', side_effect=una):
            app = self.carrega()
            self.assertEqual(list(app.exception), [])
            self.assertEqual(len([m for m in app.markdown if 'class="xifra-targeta"' in m.value]), 5)
            self.assertEqual(len([c for c in app.caption if c.value == 'MOSTRA · dades fictícies']), 4)
            app.button(key='obre-aforament').click().run(timeout=30)
            self.assertEqual(list(app.warning), [])

    def test_pic_i_llegenda_reals(self):
        from components.grafics import grafics
        from nivell1.troballes import una
        t = una('hi-cap-mati', 2, None)
        with patch('components.grafics.st.plotly_chart') as mostra:
            grafics(t)
        pic, mida = [c.args[0] for c in mostra.call_args_list]
        self.assertEqual(len(pic.layout.xaxis.ticktext), t.extra['pic'].dia.nunique())
        self.assertLess(len(pic.layout.xaxis.ticktext), len(pic.data[0].x))
        self.assertTrue(all(':' in hora for hora in pic.data[0].customdata))
        self.assertEqual([serie.name for serie in mida.data], ['Demanda', 'Oferta', 'Oferta amb seminaris'])
        self.assertEqual(pic.layout.xaxis.tickfont.color, '#24383D')
        self.assertTrue(all(c.kwargs['theme'] is None for c in mostra.call_args_list))

    def test_columnes_incompletes(self):
        app = AppTest.from_string('''
import pandas as pd
from components.grafics import dibuixa, grafics
from mostra import exemples
incompleta = pd.DataFrame({'nom': ['A']})
dibuixa(incompleta, 'heatmap', clau='mapa')
dibuixa(incompleta, 'barres', clau='barres')
t = exemples()['hi-cap-mati']
t.extra = {'pic': incompleta, 'per_mida': incompleta}
grafics(t)
''').run(timeout=30)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.warning), 4)
        self.assertEqual(len(app.dataframe), 4)


if __name__ == '__main__':
    unittest.main()

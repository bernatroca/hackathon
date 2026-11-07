"""Proves amb dades reals, sense servidor: python app/test_app.py."""
from pathlib import Path
import sys
import copy
import re
import pandas as pd
import unittest
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest

ARREL = Path(__file__).resolve().parent
sys.path.insert(0,str(ARREL.parent))
sys.path.insert(0,str(ARREL))
from nivell1.troballes import PORTADA, una
from components.grafics import grafics
from presentacio import context, proporcio, text, coll_ampolla
from servei import AULES_DISPONIBLES, AULES_RESERVA, inventari
from prova_portada import dades_inventades


def grau_inventat():
    from nivell1.troballes import Troballa
    return Troballa(id='marge-grau-nou', titol='Grau inventat', xifra='26 h',
        frase='Resum inventat', metode='Text tècnic inventat: la xifra gran és semestral.', sql='-- prova',
        taula=pd.DataFrame([{'llindar':0,'seminaris':False,'nou_hores':26.,'marge_hores':181.}]),
        extra={'setmana':'2027-W07','marge_semestre_h':4679.,'demanda_h_setmana':26.,'lliures_h_setmana':181.,
               'cap_per_mida':True,'estat_provisional':True}, exemples=['S90001'])


def respostes_inventades():
    from nivell1.troballes import Troballa
    colors = ['verd','ambre','vermell']
    return [Troballa(f'pregunta-{i+1}',f'Pregunta inventada {i+1}',str(i+1),
        'Una frase inventada per comprovar les targetes compactes.', 'Mètode inventat.', '-- prova',
        pd.DataFrame(), extra={'estat_inventat':colors[i%3]}) for i in range(11)]


def info_inventada(t):
    color = t.extra['estat_inventat']
    return dict(estat=color, etiqueta={'vermell':'Cal actuar','ambre':'Pendent de validar','verd':'Hi cap'}[color],
        titol=t.titol, frase=t.frase, c={'xifra':t.xifra})


def portada_inventada():
    return AppTest.from_string(f"""
from pathlib import Path
import streamlit as st
from prova_portada import dades_inventades
from pagines import portada
st.markdown('<style>'+Path({str(ARREL/'estil.css')!r}).read_text()+'</style>',unsafe_allow_html=True)
if 'resultats' not in st.session_state:
    st.session_state.resultats = dades_inventades()
st.session_state.semestre = 2
st.session_state.setmana = None
st.session_state.versio = ()
portada.mostra()
""").run(timeout=90)


class TestPortadaInventada(unittest.TestCase):
    def test_frases_curtes_i_mateixes_xifres_i_estats(self):
        from presentacio import text_portada
        for escenari in ('Validat', 'Pendent de validar', 'Falten aules'):
            mapa = dades_inventades(escenari)
            for id_, t in mapa.items():
                with self.subTest(escenari=escenari, id=id_):
                    detall = text(t, mapa)
                    resum = text_portada(t, detall)
                    self.assertLessEqual(len(resum['frase'].split()),15 if id_ == 'hi-cap-mati' else 12)
                    self.assertEqual(resum['c'],detall['c'])
                    self.assertEqual(resum['estat'],detall['estat'])
                    self.assertEqual(resum['etiqueta'],detall['etiqueta'])
                    self.assertEqual(resum['proposem'],detall['proposem'])

    def test_prova_autonoma_i_enllac_a_cada_caixa(self):
        # Una lectura accidental de dades fa fallar immediatament aquesta prova.
        with patch('components.vistes.una',side_effect=AssertionError('La mostra ha de ser autònoma')), \
                patch('nivell1.dades.connexio',side_effect=AssertionError('Només dades inventades')):
            app = AppTest.from_file(str(ARREL/'prova_portada.py')).run(timeout=90)
            for escenari in ('Validat', 'Pendent de validar', 'Falten aules'):
                if escenari != 'Validat':
                    app.selectbox[0].select(escenari).run(timeout=90)
                self.assertEqual(list(app.exception),[])
                self.assertEqual(list(app.error),[])
                self.assertEqual(len([b for b in app.button if b.label == 'Com ho sabem →']),len(PORTADA))
                for id_ in PORTADA[1:]:
                    caixa = next(b for b in app.get('flex_container') if b.proto.id.endswith('targeta-'+id_))
                    self.assertEqual(len(caixa.button),1)
                    self.assertEqual(caixa.button[0].label,'Com ho sabem →')
                    self.assertEqual(caixa.button[0].key,'obre-'+id_)
                html = '\n'.join(m.value for m in app.markdown)
                self.assertNotIn('Proposem:',html)
                self.assertNotIn('class="metre"',html)
                frases = re.findall(r'<p class="frase-(heroi|targeta)">(.*?)</p>',html)
                self.assertEqual(len(frases),len(PORTADA))
                for tipus, frase in frases:
                    self.assertLessEqual(len(frase.split()),15 if tipus == 'heroi' else 12)

    def test_css_text_sense_retalls_ni_alcada_fixa(self):
        css = (ARREL/'estil.css').read_text()
        contenidors = r'st-key-heroi|st-key-targetes|targeta-cor|frase-heroi|estat(?:-text)?'
        for regla in re.finditer(r'([^{}]+)\{([^{}]*)\}',css):
            selector, declaracions = regla.groups()
            if not re.search(contenidors,selector) or selector.strip() == '.estat svg':
                continue
            with self.subTest(selector=selector.strip()):
                self.assertNotRegex(declaracions,r'(?<![-\w])(?:max-)?height\s*:\s*(?!auto\b)[^;]+')
                self.assertNotRegex(declaracions,r'overflow(?:-[xy])?\s*:\s*(hidden|clip)')
                self.assertNotIn('line-clamp',declaracions)
        botons = re.search(r'\.st-key-heroi button,\.st-key-targetes button[^{}]*\{([^{}]+)\}',css)[1]
        self.assertRegex(botons,r'min-height:\s*(4[0-9]|[5-9][0-9])px')
        self.assertIn('padding:10px 12px',botons)
        self.assertRegex(css,r'\.st-key-heroi\s*\{[^}]*padding:32px;')
        self.assertIn('font:16px/1.45',css)


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
        self.assertEqual(len(app.title),1)
        self.assertTrue(any(t.value == 'Com estem avui' for t in app.title))
        # Amb el 5.2 vàlid de la part 2 la resposta passa a «Sí, hi cap».
        self.assertTrue(any(t.value in ('Hi ha marge d’hores', 'Sí, hi cap') for t in app.subheader))
        self.assertFalse(any('Sí, però just' in m.value for m in list(app.markdown)+list(app.subheader)))
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
            self.assertFalse(next(e for e in app.expander if e.label.startswith('Detalls informàtics')).proto.expanded)
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
                self.assertEqual(html.count('class="ocupacio-rajola"'),len(sales))
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

    def test_camps_nous_i_provisional(self):
        mapa = dades_inventades()
        mapa['hi-cap-mati'].extra.update(
            torns=pd.DataFrame({'torn':['mati','tarda'],'ocupacio_pct':[67.5,81.2]}),
            coll_ampolla={'llindar':88,'torn':'mati','setmana':'2027-W05'})
        mapa['hores-aula'].extra['desglos'] = {'per_assignar':4541,'laboratoris':919,'dobles':262}
        mapa['marge-grau-nou'].extra.update(estat_provisional=True,validat_part2=True)
        with patch('prova_portada.dades_inventades',return_value=mapa):
            app = portada_inventada()
        self.comprova(app)
        html = '\n'.join(m.value for m in app.markdown)
        self.assertNotIn('per assignar de debò',html)
        self.assertNotIn('El més ajustat:',html)
        self.assertIn('Matí 68 % · Tarda 81 %',text(mapa['hi-cap-mati'])['frase'])
        marge = text(mapa['marge-grau-nou'])
        self.assertEqual(marge['etiqueta'],'Pendent de validar')
        self.assertEqual(marge['estat'],'ambre')
        self.assertIn('Pendent de validar',html)
        app.button(key='obre-hores-aula').click().run(timeout=90)
        self.comprova(app)
        detall = '\n'.join(m.value for m in app.markdown)
        self.assertIn('4.541 per assignar de debò',detall)
        self.assertIn('919 laboratoris (no es toquen)',detall)
        self.assertIn('262 dobles (sense aula pròpia)',detall)

    def test_proporcions_i_metodes(self):
        from textos import TEXTOS
        self.assertEqual(proporcio(2,100),'gairebé cap (2 %)')
        self.assertEqual(proporcio(0,100),'gairebé cap (0 %)')
        self.assertEqual(proporcio(25,100),'1 de cada 4 classes')
        self.assertEqual(proporcio(74,100),'el 74 % de les classes')
        for info in TEXTOS.values():
            self.assertIn('metode_planer',info)
            self.assertIsNone(re.search(r'\b(cohort|PLAB|llindar|cota|heretades|bloc)\b',info['metode_planer'],re.I))
        marge = copy.deepcopy(una('marge-grau-nou'))
        marge.extra.pop('estat_provisional',None)
        self.assertEqual(text(marge)['etiqueta'],'Pendent de validar')

    def test_figures_sense_manipulacio(self):
        from servei import totes, versio_registre
        resultat = totes(2,None,versio_registre())
        with patch('components.grafics.st.plotly_chart') as mostra:
            for t in resultat:
                grafics(t,clau=t.id,altres={r.id:r for r in resultat})
        self.assertGreater(len(mostra.call_args_list),0)
        for crida in mostra.call_args_list:
            figura = crida.args[0]
            config = crida.kwargs['config']
            self.assertFalse(config['displayModeBar'])
            self.assertFalse(config['scrollZoom'])
            self.assertFalse(config['doubleClick'])
            self.assertFalse(config['staticPlot'])
            self.assertFalse(figura.layout.dragmode)
            self.assertTrue(figura.layout.xaxis.fixedrange)
            self.assertTrue(figura.layout.yaxis.fixedrange)

    def test_casos_singular_plural(self):
        from components.grafics import barres
        with patch('components.grafics.st.plotly_chart') as mostra:
            barres(['Un','Dos'],[1,2],'casos',' casos')
        self.assertEqual(list(mostra.call_args.args[0].data[0].text),['2 casos','1 cas'])

    @unittest.skip('AppTest no disposa de navegador ni d’una API d’amplada o viewport; no executa el CSS adaptable.')
    def test_renderitzat_estret(self):
        pass

    def test_portada_carrega_nomes_portada_i_reutilitza_cache(self):
        import servei
        import nivell1.troballes as registre
        servei.una.clear()
        esdeveniments = []
        calcula = registre.una
        titol = st.title
        navegacio = st.navigation

        def mostra_titol(*args, **kwargs):
            if args[0] == 'Com estem avui':
                esdeveniments.append('titol')
            return titol(*args, **kwargs)

        def mostra_menu(*args, **kwargs):
            esdeveniments.append('menu')
            return navegacio(*args, **kwargs)

        def pregunta(id_, *args):
            self.assertIn('menu', esdeveniments)
            self.assertIn('titol', esdeveniments)
            self.assertIn(id_, PORTADA)
            return calcula(id_, *args)

        with patch('streamlit.title',side_effect=mostra_titol), patch('streamlit.navigation',side_effect=mostra_menu), \
                patch('nivell1.troballes.una',side_effect=pregunta) as consultes, \
                patch('streamlit.spinner',wraps=st.spinner) as spinner:
            app = self.carrega()
            self.comprova(app)
            self.assertEqual([c.args[0] for c in consultes.call_args_list],list(PORTADA))
            spinner.assert_any_call('Calculant les xifres del semestre…')
            app.run(timeout=90)
            self.comprova(app)
            self.assertEqual(consultes.call_count,len(PORTADA))

    def test_coll_ampolla_general_i_percentatges_enters(self):
        for mida in (0, None, '', float('nan')):
            frase = coll_ampolla({'coll_ampolla': {'llindar':mida,'torn':'mati','setmana':'2027-W06','ocupacio_pct':69.7}})
            self.assertEqual(frase,'El més ajustat: el matí en conjunt, la setmana 2027-W06 (70 % ocupat).')
            self.assertNotIn('places',frase)
        frase = coll_ampolla({'coll_ampolla': {'llindar':88,'torn':'mati','setmana':'2027-W06','ocupacio_pct':69.7}})
        self.assertIn('les aules de més de 88 places',frase)
        t = copy.deepcopy(una('hi-cap-mati'))
        t.extra['torns'] = pd.DataFrame({'torn':['mati','tarda'],'ocupacio_pct':[69.7,42.1]})
        self.assertIn('Matí 70 % · Tarda 42 %',text(t)['frase'])

    def test_grau_nou_segons_el_5_4(self):
        from presentacio import text
        t = grau_inventat()
        t.extra['validat_part2'] = None
        self.assertEqual(text(t)['estat'],'ambre')
        t.extra['validat_part2'] = dict(valida=True, resposta=1, sessions_grau_nou_collocades=478, sessions_52_mogudes=0)
        info = text(t)
        self.assertEqual((info['estat'],info['etiqueta']),('verd','Hi cap'))
        self.assertIn('478 sessions sense moure cap classe',info['frase'])
        t.extra['validat_part2'] = dict(valida=True, resposta=2)
        self.assertEqual(text(t)['estat'],'vermell')
        t.extra['validat_part2'] = dict(valida=False, resposta=1)
        self.assertEqual(text(t)['estat'],'ambre')

    def test_hi_cap_mati_verd_quan_la_part2_ho_valida(self):
        from presentacio import text
        t = copy.deepcopy(una('hi-cap-mati'))
        t.extra.update(falla_per_mida=False, per_mida=[], per_mida_setmanes=[])
        t.extra['validat_part2'] = None
        self.assertEqual(text(t)['estat'],'ambre')
        t.extra['validat_part2'] = dict(veredicte='VALIDA AMB RELAXACIONS DECLARADES', incompliments=2, valida=False)
        self.assertEqual(text(t)['estat'],'ambre')
        t.extra['validat_part2'] = dict(veredicte='VALIDA AMB RELAXACIONS DECLARADES', incompliments=0, valida=True)
        info = text(t)
        self.assertEqual((info['estat'],info['etiqueta'],info['c']['resposta']),('verd','Hi cap','Sí, hi cap'))
        self.assertIn('verificador oficial',info['frase'])

    def test_css_injectat_alinea_targetes(self):
        app = portada_inventada()
        self.comprova(app)
        css = next(m.value for m in app.markdown if m.value.startswith('<style>'))
        self.assertIn('align-items: stretch',css)
        self.assertIn('margin-top: auto',css)
        self.assertIn('stLayoutWrapper',css)
        self.assertIn('flex-direction: column',css)
        # Cada peu conserva l'enllaç; les propostes són al detall.
        peus = [b for b in app.get('flex_container') if any('peu-targeta-' in str(v) for v in [b.proto.id])]
        self.assertEqual(len(peus),len(PORTADA)-1)
        for peu in peus:
            self.assertEqual(len(peu.button),1)
            self.assertEqual(peu.button[0].label,'Com ho sabem →')
            self.assertEqual(len(peu.markdown),0)

    def test_bloc_gran_vermell_quan_falta_mida(self):
        mapa = dades_inventades()
        t = mapa['hi-cap-mati']
        t.extra.update(falla_per_mida=True, coll_ampolla={'llindar':88,'torn':'tarda',
            'setmana':'2027-W06','demanda_h':120.,'oferta_h':100.})
        t.extra['per_mida'] = pd.DataFrame([{'llindar':88,'falla':True,'demanda_h':120.,'oferta_h':100.}])
        with patch('prova_portada.dades_inventades',return_value=mapa):
            app = portada_inventada()
        self.comprova(app)
        self.assertTrue(any('Falten aules d’algunes mides' == h.value for h in app.subheader))
        html = '\n'.join(m.value for m in app.markdown)
        self.assertIn('data-estat="vermell"',html)
        self.assertIn('Cal actuar',html)
        self.assertIn('Falta espai per a algunes mides d’aula',html)
        self.assertIn('aria-hidden="true"',html)
        app.button(key='obre-hi-cap-mati').click().run(timeout=90)
        self.comprova(app)
        detall = '\n'.join(m.value for m in app.markdown)
        self.assertIn('en falten 20 h',detall)
        self.assertIn('a la tarda',detall)
        self.assertIn('2027-W06',detall)
        t.extra['falla_per_mida'] = False
        self.assertEqual(text(t)['estat'],'vermell')

    def test_adreca_detall_franja_i_dades(self):
        app = AppTest.from_file(str(ARREL/'app.py'))
        app.query_params['resposta'] = 'fora-torn'
        app.run(timeout=90)
        self.comprova(app)
        self.assertEqual(len(app.title),1)
        self.assertTrue(any(h.value == 'Classes al torn equivocat' for h in app.header))
        self.assertTrue(any(e.label == 'Veure les dades' for e in app.expander))
        self.assertGreater(len(app.dataframe),0)
        html = '\n'.join(m.value for m in app.markdown)
        self.assertIn('2n semestre',html)
        self.assertIn('setmana típica',html)
        self.assertIn('2027-W',html)
        self.assertIn(app.query_params['resposta'],('fora-torn',['fora-torn']))
        app.button(key='torna').click().run(timeout=90)
        self.comprova(app)
        self.assertNotIn('resposta',app.query_params)
        app.button(key='obre-fora-torn').click().run(timeout=90)
        self.assertIn(app.query_params['resposta'],('fora-torn',['fora-torn']))

    def test_error_planer_sense_excepcio_visible(self):
        from errors import MISSATGE
        with patch('components.vistes.una',side_effect=RuntimeError('DETALL PRIVAT')), \
                self.assertLogs('espais.part1',level='ERROR'):
            app = self.carrega()
        self.assertEqual(list(app.exception),[])
        self.assertGreater(len(app.error),0)
        self.assertTrue(all(e.value == MISSATGE for e in app.error))
        self.assertFalse(any('DETALL PRIVAT' in m.value for m in app.markdown))

    def test_taula_completa_i_barres_limitades(self):
        from components.grafics import barres
        app = AppTest.from_string("""
import pandas as pd
from components.grafics import barres
from components.taules import mostra_taula
barres([str(i) for i in range(12)],list(range(12)),'casos',' casos')
with __import__('streamlit').expander('Veure les dades'):
    mostra_taula(pd.DataFrame({'hores':list(range(12))}))
""").run(timeout=90)
        self.comprova(app)
        self.assertTrue(any(c.value == 'Es mostren els 8 casos amb el valor més alt.' for c in app.caption))
        self.assertEqual(len(app.dataframe[0].value),12)
        self.assertIn('Temps d’espera (h)',app.dataframe[0].value.columns)
        with patch('components.grafics.st.plotly_chart') as mostra:
            barres(['A','B'],[1,2],'petit')
        fig = mostra.call_args.args[0]
        self.assertEqual(fig.data[0].marker.cornerradius,4)
        self.assertLessEqual((fig.layout.height-60)/2 * fig.data[0].width,24)

    def test_part2_amb_css_compartit(self):
        app = AppTest.from_string(f"""
from pathlib import Path
import streamlit as st
from pagines import part2
st.markdown('<style>'+Path({str(ARREL/'estil.css')!r}).read_text()+'</style>',unsafe_allow_html=True)
st.title('Part 2 · Proposta d’horari')
part2.mostra()
""").run(timeout=90)
        self.assertEqual(list(app.exception),[])
        self.assertEqual(list(app.error),[])
        self.assertTrue(any(h.value == 'La setmana del grup' for h in app.subheader))

    def test_grau_nou_tres_magnituds_inventades(self):
        t = grau_inventat()
        info = text(t)
        self.assertEqual(info['c']['hores_noves'],'26')
        self.assertEqual(info['c']['hores_lliures'],'181')
        self.assertEqual(info['c']['marge_semestre'],'4.679')
        self.assertIn('setmana seleccionada',text(t,setmana_triada='2027-W07')['frase'])
        app = AppTest.from_string("""
import streamlit as st
from test_app import grau_inventat
from components.vistes import targeta, detall
st.session_state.resultats = {}
st.session_state.setmana = None
t = grau_inventat()
targeta(t)
detall(t)
""").run(timeout=90)
        self.comprova(app)
        html = '\n'.join(m.value for m in app.markdown)
        self.assertEqual(html.count('a la setmana que necessita'),2)  # només al detall
        self.assertEqual(html.count('de marge en tot el semestre'),2)
        self.assertIn('lliures a la setmana més plena',html)
        self.assertIn('26 h',html)
        self.assertIn('181 h',html)
        self.assertIn('4.679 h',html)
        self.assertFalse(any('S90001' in c.value for c in app.code))
        self.assertEqual(t.metode,'Text tècnic inventat: la xifra gran és semestral.')

    def test_columnes_privades_i_resum_docents_inventats(self):
        from components.taules import filtra_columnes, taula_presentacio
        from nivell1.troballes import Troballa
        df = pd.DataFrame({'docent':['D900','D901','D902'],'dies_mati_tarda':[1,2,2],
            'a_cavall':[True]*3,'dies':['L','L,M','M,X'], 'exemples':[['S90001']]*3,
            'codi':['100000']*3,'assignatura':['Assignatura Inventada I']*3})
        filtrada = filtra_columnes(df)
        self.assertNotIn('docent',filtrada)
        self.assertNotIn('codi',filtrada)
        self.assertNotIn('assignatura',filtrada)
        self.assertNotIn('exemples',filtrada)
        t = Troballa('docents-cavall','Prova','3','Prova','Prova','-- prova',df)
        resum = taula_presentacio(t)
        self.assertEqual(set(resum.columns),{'dies_mati_tarda','docents_recompte'})
        self.assertEqual(int(resum.docents_recompte.sum()),3)
        with patch('components.grafics.st.plotly_chart') as mostra:
            grafics(t)
        fig = mostra.call_args.args[0]
        self.assertFalse(any('D90' in nom for nom in fig.data[0].y))
        self.assertEqual(int(sum(fig.data[0].x)),3)

    def test_marges_barres_inventades(self):
        from components.grafics import barres
        with patch('components.grafics.st.plotly_chart') as mostra:
            barres(['GXX · 3r'],[64],'prova',' classes')
        fig = mostra.call_args.args[0]
        self.assertGreaterEqual(fig.layout.margin.r,120)
        self.assertEqual(fig.layout.yaxis.ticklabelstandoff,12)
        self.assertTrue(fig.data[0].texttemplate.startswith('\u2009\u2009\u2009'))
        self.assertFalse(fig.data[0].cliponaxis)

    def test_respostes_ordre_per_urgencia(self):
        from presentacio import ordena_respostes, grup_estat
        resultat = respostes_inventades()
        infos = {t.id:info_inventada(t) for t in resultat}
        ordenades = ordena_respostes(resultat, infos)
        self.assertEqual([t.id for t in ordenades],
            ['pregunta-3','pregunta-6','pregunta-9','pregunta-2','pregunta-5',
             'pregunta-8','pregunta-11','pregunta-1','pregunta-4','pregunta-7','pregunta-10'])
        self.assertEqual(grup_estat(infos['pregunta-2']),'Vigilar')

    def test_respostes_compactes_filtres_i_comptador(self):
        app = AppTest.from_string("""
import streamlit as st
from unittest.mock import patch
from test_app import respostes_inventades, info_inventada
from pagines import preguntes
st.session_state.semestre = 2
st.session_state.setmana = None
st.session_state.versio = ()
with patch('pagines.preguntes.totes',return_value=respostes_inventades()), patch('pagines.preguntes.contingut',side_effect=info_inventada):
    preguntes.mostra()
""").run(timeout=90)
        self.comprova(app)
        def targetes():
            return [m.value for m in app.markdown if '<article class="resposta-compacta"' in m.value]
        self.assertEqual(len(targetes()),11)
        self.assertEqual([b.key for b in app.button],
            ['obre-pregunta-3','obre-pregunta-6','obre-pregunta-9','obre-pregunta-2',
             'obre-pregunta-5','obre-pregunta-8','obre-pregunta-11','obre-pregunta-1',
             'obre-pregunta-4','obre-pregunta-7','obre-pregunta-10'])
        self.assertTrue(any('Es mostren 11 de 11' in m.value for m in app.markdown))
        self.assertFalse(any('class="proposem"' in m.value or 'class="metre"' in m.value for m in app.markdown))
        self.assertEqual(app.get('button_group')[0].proto.label,'Estat')
        self.assertEqual(app.multiselect[0].label,'Respostes')
        app.get('button_group')[0].set_value(['Cal actuar']).run(timeout=90)
        self.comprova(app)
        self.assertEqual(len(targetes()),3)
        self.assertTrue(any('Es mostren 3 de 11' in m.value for m in app.markdown))
        app.multiselect[0].set_value(['pregunta-3']).run(timeout=90)
        self.comprova(app)
        self.assertEqual(len(targetes()),1)
        self.assertTrue(any('Es mostren 1 de 11' in m.value for m in app.markdown))
        app.multiselect[0].set_value([]).run(timeout=90)
        self.assertEqual(len(targetes()),3)
        app.get('button_group')[0].set_value(['Vigilar']).run(timeout=90)
        self.assertEqual(len(targetes()),4)
        self.assertTrue(all('Pendent de validar' in h for h in targetes()))
        app.get('button_group')[0].set_value([]).run(timeout=90)
        self.comprova(app)
        self.assertEqual(len(targetes()),0)
        self.assertTrue(any('Es mostren 0 de 11' in m.value for m in app.markdown))

    def test_canvi_semestre(self):
        app = self.carrega()
        app.selectbox[0].select(1).run(timeout=90)
        self.comprova(app)
        self.assertEqual(len([b for b in app.button if b.label == 'Com ho sabem →']),len(PORTADA))
        app.selectbox[1].select_index(1).run(timeout=90)
        self.comprova(app)


if __name__ == '__main__':
    unittest.main()

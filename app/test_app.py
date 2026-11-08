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
    return Troballa(id='marge-grau-nou', titol='Grau inventat', xifra='27 h',
        frase='Resum inventat', metode='Text tècnic inventat: la xifra gran és semestral.', sql='-- prova',
        taula=pd.DataFrame([{'llindar':0,'seminaris':False,'nou_hores':27.,'marge_hores':173.}]),
        extra={'setmana':'2027-W06','criteri_setmana':'demanda_mati','demanda_h_setmana':27.,'lliures_h_setmana':173.,
               'cap_per_mida':True,'estat_provisional':True}, exemples=['S90001'])


def respostes_inventades():
    from nivell1.troballes import Troballa
    colors = ['gris','verd','ambre']
    return [Troballa(f'pregunta-{i+1}',f'Pregunta inventada {i+1}',str(i+1),
        'Una frase inventada per comprovar les targetes compactes.', 'Mètode inventat.', '-- prova',
        pd.DataFrame(), extra={'estat_inventat':colors[i%3]}) for i in range(11)]


def info_inventada(t):
    color = t.extra['estat_inventat']
    return dict(estat=color, etiqueta={'ambre':'Cal decidir','verd':'Resolt amb la proposta','gris':'Per saber-ho'}[color],
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
                    self.assertTrue(resum['titol'].endswith('?'))
                    self.assertEqual(resum['frase'], detall['frase'])
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
                self.assertEqual(len([b for b in app.button if (b.key or '').startswith('obre-')]),len(PORTADA))
                for id_ in PORTADA[1:]:
                    caixa = next(b for b in app.get('flex_container') if b.proto.id.endswith('targeta-'+id_))
                    self.assertEqual(len(caixa.button),1)
                    self.assertTrue(caixa.button[0].label.startswith('Mira '))
                    self.assertEqual(caixa.button[0].key,'obre-'+id_)
                html = '\n'.join(m.value for m in app.markdown)
                self.assertIn('Què vol dir</b>',html)
                self.assertNotIn('class="metre"',html)
                frases = re.findall(r'<p class="frase-(heroi|targeta)">(.*?)</p>',html)
                self.assertEqual(len(frases),len(PORTADA))
                for tipus, frase in frases:
                    self.assertIn('Què vol dir', frase)

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
        self.assertTrue(any(t.value in ('Per comprovar', 'Sí') for t in app.subheader))
        self.assertFalse(any('Sí, però just' in m.value for m in list(app.markdown)+list(app.subheader)))
        self.assertEqual(len([m for m in app.markdown if 'class="xifra-targeta"' in m.value]),len(PORTADA)-1)
        self.assertEqual(len([b for b in app.button if (b.key or '').startswith('obre-')]),len(PORTADA))
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
        self.assertEqual(len([b for b in app.button if (b.key or '').startswith('obre-')]),len(ids))
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
        self.assertIn('12 de les 19 aules',text(mapa['hi-cap-mati'])['frase'])
        marge = text(mapa['marge-grau-nou'])
        self.assertEqual(marge['etiqueta'],'Cal decidir')
        self.assertEqual(marge['estat'],'ambre')
        self.assertIn('Cal decidir',html)
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
        self.assertEqual(text(marge)['etiqueta'],'Cal decidir')

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
            self.assertEqual(frase,'El més ajustat: el matí en conjunt, la setmana del 8/2 – 12/2 (70 % ocupat).')
            self.assertNotIn('places',frase)
        frase = coll_ampolla({'coll_ampolla': {'llindar':88,'torn':'mati','setmana':'2027-W06','ocupacio_pct':69.7}})
        self.assertIn('les aules de més de 88 places',frase)
        t = copy.deepcopy(una('hi-cap-mati'))
        t.extra['torns'] = pd.DataFrame({'torn':['mati','tarda'],'ocupacio_pct':[69.7,42.1]})
        self.assertIn('de les 19 aules',text(t)['frase'])

    def test_regressions_portada_ronda6_inventades(self):
        mapa = dades_inventades('Validat')
        t = grau_inventat()
        t.extra.update(estat_provisional=False, validat_part2=dict(
            valida=True, resposta=1, sessions_grau_nou_collocades=317,
            sessions_grau_nou_fora_franja=29, sessions_52_mogudes=0))
        mapa['marge-grau-nou'] = t
        with patch('prova_portada.dades_inventades', return_value=mapa):
            app = portada_inventada()
        self.comprova(app)
        hero = next(b for b in app.get('flex_container') if b.proto.id.endswith('-heroi'))
        self.assertTrue(any('estat verd' in m.value and 'Resolt amb la proposta' in m.value for m in hero.markdown))
        caixa = next(b for b in app.get('flex_container') if b.proto.id.endswith('targeta-marge-grau-nou'))
        html = '\n'.join(m.value for m in caixa.markdown)
        self.assertIn('317 classes del grau nou', html)
        self.assertNotIn('5.2', html)
        self.assertIn('Què vol dir', html)
        self.assertIn('sense moure cap classe', html)
        from components.vistes import targeta_compacta
        app = AppTest.from_string("""
from test_app import grau_inventat
from components.vistes import targeta_compacta, estil_respostes
estil_respostes()
targeta_compacta(grau_inventat())
""").run(timeout=90)
        self.comprova(app)
        html = '\n'.join(m.value for m in app.markdown)
        self.assertIn('27 h a la setmana', html)
        self.assertIn('173 h lliures', html)
        self.assertNotIn('de marge en tot el semestre', html)
        self.assertNotIn('-webkit-line-clamp:3', html)

    def test_grau_nou_segons_el_5_4(self):
        from presentacio import text
        t = grau_inventat()
        t.extra['validat_part2'] = None
        self.assertEqual(text(t)['estat'],'ambre')
        t.extra['validat_part2'] = dict(valida=True, resposta=1, sessions_grau_nou_collocades=478,
                                      sessions_52_mogudes=0, sessions_grau_nou_fora_franja=235)
        info = text(t)
        self.assertEqual((info['estat'],info['etiqueta']),('verd','Resolt amb la proposta'))
        self.assertIn('478 classes',info['frase'])
        self.assertIn('235 classes noves queden en una hora diferent de la que demanaven per reduir esperes',info['frase'])
        self.assertIn('sense moure cap classe de la resta de l’horari',info['frase'])
        self.assertIn('sense moure cap classe',info['frase'])
        t.extra['validat_part2'].update(sessions_grau_nou_fora_franja=0, sessions_52_mogudes=2)
        self.assertIn('totes les classes noves conserven l’hora que demanaven',text(t)['frase'])
        self.assertIn('movent 2 classes de la resta de l’horari',text(t)['frase'])
        t.extra['validat_part2'] = dict(valida=True, resposta=2)
        self.assertEqual(text(t)['estat'],'ambre')
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
        self.assertEqual((info['estat'],info['etiqueta'],info['c']['resposta']),('verd','Resolt amb la proposta','Sí'))
        self.assertNotIn('verificador oficial',info['frase'])

    def test_css_injectat_alinea_targetes(self):
        app = portada_inventada()
        self.comprova(app)
        css = next(m.value for m in app.markdown if m.value.startswith('<style>'))
        self.assertIn('align-items: stretch',css)
        self.assertIn('margin-top: auto',css)
        self.assertIn('stLayoutWrapper',css)
        self.assertIn('flex-direction: column',css)
        # Cada peu conserva la proposta visible i l'enllaç.
        peus = [b for b in app.get('flex_container') if any('peu-targeta-' in str(v) for v in [b.proto.id])]
        self.assertEqual(len(peus),len(PORTADA)-1)
        for peu in peus:
            self.assertEqual(len(peu.button),1)
            self.assertTrue(peu.button[0].label.startswith('Mira '))
            propostes = [m for m in peu.markdown if 'class="proposem"' in m.value]
            self.assertEqual(len(propostes),0)

    def test_bloc_gran_vermell_quan_falta_mida(self):
        mapa = dades_inventades()
        t = mapa['hi-cap-mati']
        t.extra.update(falla_per_mida=True, coll_ampolla={'llindar':88,'torn':'tarda',
            'setmana':'2027-W06','demanda_h':120.,'oferta_h':100.})
        t.extra['per_mida'] = pd.DataFrame([{'llindar':88,'falla':True,'demanda_h':120.,'oferta_h':100.}])
        with patch('prova_portada.dades_inventades',return_value=mapa):
            app = portada_inventada()
        self.comprova(app)
        self.assertTrue(any('No' == h.value for h in app.subheader))
        html = '\n'.join(m.value for m in app.markdown)
        self.assertIn('data-estat="ambre"',html)
        self.assertIn('Cal decidir',html)
        self.assertIn('Falta espai per a algunes mides d’aula',html)
        self.assertIn('aria-hidden="true"',html)
        app.button(key='obre-hi-cap-mati').click().run(timeout=90)
        self.comprova(app)
        detall = '\n'.join(m.value for m in app.markdown)
        self.assertIn('en falten 20 h',detall)
        self.assertIn('a la tarda',detall)
        self.assertIn('8/2 – 12/2',detall)
        t.extra['falla_per_mida'] = False
        self.assertEqual(text(t)['estat'],'ambre')

    def test_adreca_detall_franja_i_dades(self):
        app = AppTest.from_file(str(ARREL/'app.py'))
        app.query_params['resposta'] = 'fora-torn'
        app.run(timeout=90)
        self.comprova(app)
        self.assertEqual(len(app.title),1)
        self.assertTrue(any(h.value == 'Quantes classes són al torn equivocat?' for h in app.header))
        self.assertTrue(any(e.label == 'Detall tècnic: veure les dades' for e in app.expander))
        self.assertGreater(len(app.dataframe),0)
        html = '\n'.join(m.value for m in app.markdown)
        self.assertIn('2n semestre',html)
        self.assertIn('setmana típica',html)
        self.assertRegex(html, r'\d{1,2}/\d{1,2} – \d{1,2}/\d{1,2}')
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

    def test_grau_nou_comparacio_setmanal_inventada(self):
        t = grau_inventat()
        info = text(t)
        self.assertEqual(info['c']['hores_noves'],'27')
        self.assertEqual(info['c']['hores_lliures'],'173')
        self.assertEqual(info['c']['marge_semestre'],'—')
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
        self.assertIn('El grau necessita 27 h a la setmana',html)
        self.assertNotIn('de marge en tot el semestre',html)
        self.assertIn('lliures a la setmana amb més demanda de matí',html)
        self.assertIn('27 h',html)
        self.assertIn('173 h',html)
        self.assertNotIn('4.679 h',html)
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
        self.assertEqual(grup_estat(infos['pregunta-2']),'Resolt amb la proposta')

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
        self.assertTrue(any('Prova: deixa només «Cal decidir»' in c.value for c in app.caption))
        self.assertTrue(any('Pas següent: mira l’horari proposat →' in m.value for m in app.markdown))
        self.assertEqual([b.key for b in app.button],
            ['obre-pregunta-3','obre-pregunta-6','obre-pregunta-9','obre-pregunta-2',
             'obre-pregunta-5','obre-pregunta-8','obre-pregunta-11','obre-pregunta-1',
             'obre-pregunta-4','obre-pregunta-7','obre-pregunta-10'])
        self.assertTrue(any('Es mostren 11 de 11' in m.value for m in app.markdown))
        self.assertFalse(any('class="proposem"' in m.value or 'class="metre"' in m.value for m in app.markdown))
        self.assertEqual(app.get('button_group')[0].proto.label,'Estat')
        self.assertEqual(app.multiselect[0].label,'Respostes')
        app.get('button_group')[0].set_value(['Cal decidir']).run(timeout=90)
        self.comprova(app)
        self.assertEqual(len(targetes()),3)
        self.assertTrue(any('Es mostren 3 de 11' in m.value for m in app.markdown))
        app.multiselect[0].set_value(['pregunta-3']).run(timeout=90)
        self.comprova(app)
        self.assertEqual(len(targetes()),1)
        self.assertTrue(any('Es mostren 1 de 11' in m.value for m in app.markdown))
        app.multiselect[0].set_value([]).run(timeout=90)
        self.assertEqual(len(targetes()),3)
        app.get('button_group')[0].set_value(['Resolt amb la proposta']).run(timeout=90)
        self.assertEqual(len(targetes()),4)
        self.assertTrue(all('Resolt amb la proposta' in h for h in targetes()))
        app.get('button_group')[0].set_value([]).run(timeout=90)
        self.comprova(app)
        self.assertEqual(len(targetes()),0)
        self.assertTrue(any('Pas següent: mira l’horari proposat →' in m.value for m in app.markdown))
        self.assertTrue(any('Es mostren 0 de 11' in m.value for m in app.markdown))

    def test_canvi_semestre(self):
        app = self.carrega()
        app.selectbox[0].select(1).run(timeout=90)
        self.comprova(app)
        self.assertEqual(len([b for b in app.button if (b.key or '').startswith('obre-')]),len(PORTADA))
        app.selectbox[1].select_index(1).run(timeout=90)
        self.comprova(app)


class TestAuditoriaInventada(unittest.TestCase):
    def troballa(self, id_, taula=None, extra=None, xifra='1'):
        from nivell1.troballes import Troballa
        return Troballa(id_, 'Pregunta inventada', xifra, 'Frase inventada',
                        'Mètode inventat', '-- prova',
                        pd.DataFrame() if taula is None else taula, extra=extra or {})

    def test_cobertura_llindar_i_avis(self):
        for n, estat in ((2, 'ambre'), (5, 'ambre'), (74, 'ambre')):
            with self.subTest(n=n):
                cobertura = self.troballa('hores-aula', pd.DataFrame({'sessions_totals':[100]}),
                                          {'sessions_sense_aula':n})
                self.assertEqual(text(cobertura)['estat'], estat)
                self.assertNotIn('aproximadament', text(cobertura)['frase'])
                with patch('components.grafics.planol'), patch('components.grafics.st.info') as avis:
                    grafics(self.troballa('ocupacio'), altres={'hores-aula':cobertura})
                self.assertEqual(avis.call_count, int(n >= 5))
                if n >= 5:
                    self.assertIn('no tenen aula assignada', avis.call_args.args[0])

    def test_dies_en_ordre_i_referencia(self):
        t = self.troballa('hores-aula', pd.DataFrame({'dia':['V','M','L','J','X'],
                            'demanda':[7,9,6,8,5]}))
        with patch('components.grafics.st.plotly_chart') as mostra:
            grafics(t)
        fig = mostra.call_args.args[0]
        self.assertEqual(list(fig.data[0].x), ['Dilluns','Dimarts','Dimecres','Dijous','Divendres'])
        self.assertEqual(list(fig.data[0].y), [6,9,5,8,7])
        self.assertEqual(fig.layout.shapes[0].y0, 19)

    def test_tots_els_singulars(self):
        from components.grafics import barres, SINGULAR
        for plural, singular in SINGULAR.items():
            with self.subTest(unitat=plural), patch('components.grafics.st.plotly_chart') as mostra:
                barres(['Inventat'], [1], 'prova', plural)
                self.assertEqual(list(mostra.call_args.args[0].data[0].text), ['1'+singular])

    def test_docents_sense_dies_no_apareixen(self):
        from components.taules import resum_docents
        for dies in ([0,0], [0,1,2]):
            df = pd.DataFrame({'dies_mati_tarda':dies})
            self.assertTrue((resum_docents(df).dies_mati_tarda > 0).all())
            with patch('components.grafics.st.plotly_chart') as mostra, patch('components.grafics.st.info') as avis:
                grafics(self.troballa('docents-cavall', df))
            self.assertEqual(mostra.call_count, int(any(dies)))
            if not any(dies):
                self.assertIn('cap docent', avis.call_args.args[0])

    def test_fora_torn_semestre_encara_que_setmana_buida(self):
        from components.taules import taula_presentacio
        t = self.troballa('fora-torn', pd.DataFrame(columns=['cohort','sessions']),
            {'per_cohort':pd.DataFrame({'abast':['semestre','setmana'],
                 'cohort':['GXX:1r','GXX:1r'], 'sessions':[12,0]})})
        with patch('components.grafics.st.plotly_chart') as mostra:
            grafics(t)
        self.assertEqual(list(mostra.call_args.args[0].data[0].x), [12])
        self.assertEqual(list(taula_presentacio(t).sessions), [12])

    def test_dates_context_i_criteris(self):
        from presentacio import dates_setmana, etiqueta_setmana
        from components.vistes import franja_context
        self.assertEqual(dates_setmana('2027-W06'), '8/2 – 12/2')
        self.assertIn('més classes alhora (8/2 – 12/2)', etiqueta_setmana('2027-W06'))
        self.assertIn('més demanda de matí', etiqueta_setmana('2027-W06','demanda_mati'))
        self.assertIn('sense dades', franja_context(2,None))
        html = franja_context(2,('2027-W06', '2027-02-08', 500))
        self.assertIn('8/2 – 12/2 · 500 classes', html)
        self.assertNotIn('2027-W', html)

    def test_aforament_amb_tots_els_casos(self):
        t = self.troballa('aforament', extra={'sessions_total':101,
            'sessions_heretades':58, 'grups_afectats':6}, xifra='43')
        frase = text(t)['frase']
        for fragment in ('101 classes', '6 grups', '43 classes on no hi caben tots els alumnes es poden corregir', '58 són de grups fixats'):
            self.assertIn(fragment, frase)

    def test_validats_sense_metode_provisional(self):
        for id_ in ('hi-cap-mati', 'marge-grau-nou'):
            t = dades_inventades()[id_]
            info = text(t)
            self.assertIn('ho confirma: comprovat', info['metode_planer'])
            self.assertNotIn('encara', info['metode_planer'])
            self.assertNotIn('5.2', info['frase'])
            if id_ == 'hi-cap-mati':
                self.assertEqual(info['proposem'], 'Aplicar l’horari proposat.')

    def test_error_no_recarrega_la_mateixa_pregunta(self):
        app = AppTest.from_string("""
import streamlit as st
from unittest.mock import patch
from components.vistes import carrega, carrega_grup
st.session_state.resultats = {}
st.session_state.semestre = 2
st.session_state.setmana = None
st.session_state.versio = ()
with patch('components.vistes.una', side_effect=RuntimeError('Error inventat')) as consulta, patch('components.vistes.mostra_error'):
    carrega_grup(['hores-aula'])
    carrega('hores-aula')
    st.write('Consultes: ' + str(consulta.call_count))
""").run(timeout=90)
        self.assertEqual(list(app.exception), [])
        self.assertTrue(any(m.value == 'Consultes: 1' for m in app.markdown))

    def test_setmanes_lectives_i_ocupacio_amb_mateixa_base(self):
        import duckdb
        con = duckdb.connect(':memory:')
        try:
            con.execute("""CREATE TABLE sessions(id_sessio VARCHAR, sem INTEGER,
                setmana VARCHAR, data DATE, aula_partida VARCHAR,
                aules_addicionals_partida VARCHAR, sense_espai BOOLEAN)""")
            # Quatre classes, dues (exactament 50 %) i una: només dues setmanes lectives.
            files = [(f'S{90000+i}', 2, setmana, data, 'Q9/0001', '', False)
                     for i,(setmana,data) in enumerate([
                         ('2027-W06','2027-02-08'),('2027-W06','2027-02-09'),
                         ('2027-W06','2027-02-10'),('2027-W06','2027-02-11'),
                         ('2027-W07','2027-02-15'),('2027-W07','2027-02-16'),
                         ('2027-W08','2027-02-22')])]
            con.executemany('INSERT INTO sessions VALUES (?,?,?,?,?,?,?)', files)
            con.execute("CREATE TABLE aules AS SELECT 'Q9/0001' AS aula")
            con.execute('CREATE TABLE sessio_blocs AS SELECT id_sessio, 0 AS bloc FROM sessions')
            consultes = ARREL.parent/'nivell1'/'consultes'
            params = {'semestre':2,'setmana':None}
            setmanes = con.execute((consultes/'semestre_setmanes.sql').read_text(), params).fetchone()[0]
            self.assertEqual(setmanes, 2)
            ocupacio = con.execute((consultes/'ocupacio_resum.sql').read_text(), params).fetchone()[1]
            self.assertAlmostEqual(ocupacio, 100*6/(2*125))
        finally:
            con.close()


    def test_propostes_resoltes_nomes_amb_validacio(self):
        for id_ in ('hores-aula', 'fora-torn', 'aforament', 'ocupacio'):
            t = self.troballa(id_, extra={'sessions_total':11, 'sessions_heretades':4}, xifra='7')
            pendent = text(t)
            t.extra['validat_part2'] = {'valida': True}
            validada = text(t)
            self.assertNotIn('verificador oficial', validada['proposem'])
            self.assertTrue(validada['c']['proposta_validada'])
            self.assertEqual(validada['c']['xifra'], pendent['c']['xifra'])
            self.assertEqual(validada['estat'], 'gris' if id_ == 'ocupacio' else 'verd')
            if id_ == 'aforament':
                self.assertTrue(validada['frase'].startswith('7 classes'))
                self.assertIn('corregeix les 7 classes; les 4', validada['proposem'])
            t.extra['validat_part2'] = {'valida': False}
            self.assertNotIn('verificador oficial', text(t)['proposem'])

    def test_peus_expliquen_setmana_del_pic_i_del_detall(self):
        app = portada_inventada()
        self.assertEqual(list(app.exception), [])
        self.assertTrue(any('moment més ple, setmana del' in m.value for m in app.markdown))
        app.button(key='obre-hi-cap-mati').click().run(timeout=30)
        captions = ' '.join(c.value for c in app.caption)
        self.assertIn('la comparació mostra la setmana amb més classes alhora', captions)
        self.assertNotIn('setmana seleccionada', captions)

    def test_docents_expliquen_el_torn_de_cada_classe(self):
        info = text(self.troballa('docents-cavall', xifra='17'))
        self.assertIn('Segons el torn que li toca a cada classe', info['frase'])
        self.assertIn('segons el torn que li toca a cada classe', info['metode_planer'])
        self.assertIn('17 docents', info['frase'])


class TestValidacioPart2Inventada(unittest.TestCase):
    def test_sha_i_recomptes_del_servei(self):
        import hashlib
        import json
        import tempfile
        import servei
        from components.vistes import frase_grau
        with tempfile.TemporaryDirectory() as temporal:
            arrel = Path(temporal)
            carpeta = arrel / '5.4'
            carpeta.mkdir()
            proposta = b'sessio,aula\nINVENTADA,AULA-INVENTADA\n'
            (carpeta / 'proposta.csv').write_bytes(proposta)
            informe = dict(veredicte='VALIDA', context=dict(
                proposta_sha256=hashlib.sha256(proposta).hexdigest()))
            (carpeta / 'informe.json').write_text(json.dumps(informe))
            (carpeta / 'resum.json').write_text(json.dumps(dict(
                resposta=1, sessions_grau_nou_collocades=235,
                sessions_grau_nou_fora_franja=29, sessions_52_mogudes=0)))
            with patch.object(servei, 'RESULTATS_PART2', arrel):
                t = grau_inventat()
                t.extra['validat_part2'] = servei.validacio_part2('5.4')
                self.assertEqual(t.extra['validat_part2']['sessions_grau_nou_fora_franja'], 29)
                self.assertEqual(t.extra['validat_part2']['sessions_52_mogudes'], 0)
                # La presentació no torna a llegir el resum.
                with patch.object(Path, 'read_text', side_effect=AssertionError('Lectura duplicada')):
                    info = text(t)
                    frase = frase_grau(t, info)
                self.assertIn('235 classes', frase)
                self.assertIn('29 classes noves queden en una hora diferent de la que demanaven per reduir esperes', frase)
                self.assertIn('sense moure cap classe de la resta de l’horari', frase)
                (carpeta / 'proposta.csv').write_bytes(proposta + b'CANVIADA,AULA\n')
                t.extra['validat_part2'] = servei.validacio_part2('5.4')
                info = text(t)
                self.assertNotEqual(info['estat'], 'verd')
                self.assertEqual(info['etiqueta'], 'Cal decidir')


class TestClassesInventades(unittest.TestCase):
    def files(self):
        return pd.DataFrame([
            dict(id_sessio='S90001', assignatura='Assignatura Inventada I', grup='TE/81',
                 data='2027-02-15', dia='L', h_ini='08:30', h_fi='10:30',
                 titulacions_curs='GXX:1r|GYY:2n', torn_actual='mati', torn_requerit='tarda'),
            dict(id_sessio='S90002', assignatura='Assignatura Inventada II', grup='PAUL/811',
                 data='2027-02-16', dia='M', h_ini='15:00', h_fi='17:00',
                 titulacions_curs='GXX:2n', torn_actual='tarda', torn_requerit='mati'),
            dict(id_sessio='S90003', assignatura='Assignatura Inventada III', grup='TE/82',
                 data='2027-02-17', dia='X', h_ini='08:30', h_fi='10:30',
                 titulacions_curs='', torn_actual='mati', torn_requerit='tarda')])

    def test_filtres_parelles_i_noms(self):
        from components.taules import filtra_classes, taula_classes
        df = self.files()
        self.assertEqual(len(filtra_classes(df)), 3)
        self.assertEqual(len(filtra_classes(df, 'GXX', '1r')), 1)
        self.assertEqual(len(filtra_classes(df, 'GXX', '2n')), 1)
        self.assertEqual(len(filtra_classes(df, 'GYY', '1r')), 0)
        self.assertEqual(len(filtra_classes(df, 'GYY', '2n')), 1)
        taula = taula_classes(df)
        self.assertEqual(len(taula), 3)
        self.assertIn('Assignatura', taula)
        self.assertIn('Torn que té', taula)
        self.assertIn('Torn que li toca', taula)
        self.assertNotIn('id_sessio', taula)
        self.assertEqual(taula.iloc[0]['Assignatura'], 'Assignatura Inventada I')
        self.assertEqual(taula.iloc[0]['Dia'], 'Dilluns')
        self.assertEqual(taula.iloc[0]['Torn que té'], 'Matí')
        self.assertEqual(taula.iloc[0]['Data'], '15/02/2027')

    def test_filtres_visibles_i_recompte_sense_lectures(self):
        app = AppTest.from_string("""
import streamlit as st
from unittest.mock import patch
from test_app import TestClassesInventades
from nivell1.troballes import Troballa
from components.taules import mostra_classes
st.session_state.semestre = 2
t = Troballa('fora-torn', 'Inventat', '3', 'Inventat', 'Inventat', '-- prova',
    __import__('pandas').DataFrame(), extra={'classes_detall': TestClassesInventades().files()})
with patch('servei.classes_detall', side_effect=AssertionError('Només dades inventades')):
    mostra_classes(t)
""").run(timeout=30)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.dataframe[0].value), 3)
        app.selectbox(key='classes-titulacio-fora-torn').select('GYY').run()
        self.assertEqual(len(app.dataframe[0].value), 1)
        self.assertTrue(any('1 classes amb aquests filtres · 3 classes en total' in m.value for m in app.markdown))
        app.selectbox(key='classes-curs-fora-torn').select('1r').run()
        self.assertEqual(len(app.dataframe), 0)
        self.assertTrue(any('Cap classe coincideix' in e.value for e in app.info))

    def test_consultes_exclouen_fixades_laboratoris_i_dobles(self):
        import duckdb
        from nivell1.dades import CONSULTES
        con = duckdb.connect(':memory:')
        try:
            df = self.files()
            df['sem'] = 2
            df['aula_partida'] = None
            df['demanda_aulari'] = [True, False, False]
            df['fixada'] = ['', '', 'R1: GXX 1r']
            con.register('sessions', df)
            sense = con.execute((CONSULTES / 'hores_aula_classes.sql').read_text(), {'semestre': 2}).df()
            fora = con.execute((CONSULTES / 'fora_torn_classes.sql').read_text(), {'semestre': 2}).df()
            self.assertEqual(len(sense), 1)
            self.assertEqual(len(fora), 2)
            self.assertEqual(len(con.execute((CONSULTES / 'fora_torn_classes.sql').read_text(), {'semestre': 1}).df()), 0)
        finally:
            con.close()

    def test_comparacio_i_estats_amb_recomptes_inventats(self):
        t = dades_inventades()['hores-aula']
        t.extra['validat_part2'] = {'valida': True, 'restriccions': {
            'R5-SENSE-AULA': {'compten': 0, 'declarades': 0, 'heretades': 12}}}
        info = text(t)
        self.assertEqual(info['c']['xifra'], '30 classes')
        self.assertEqual(info['c']['comparacio'], 'Avui 30 classes → 0 classes amb la proposta')
        self.assertEqual(info['etiqueta'], 'Resolt amb la proposta')
        t.extra['validat_part2'] = None
        self.assertEqual(text(t)['c']['comparacio'], '')
        self.assertEqual(text(t)['etiqueta'], 'Cal decidir')

    def test_files_reals_coincideixen_amb_els_recomptes(self):
        from nivell1.preguntes import hores_aula, fora_torn
        for semestre in (1, 2):
            sense = hores_aula.calcula(semestre)
            self.assertEqual(len(hores_aula.classes(semestre)), sense.extra['desglos']['per_assignar'])
            fora = fora_torn.calcula(semestre)
            self.assertEqual(len(fora_torn.classes(semestre)), int(valor_fora(fora.xifra)))

    def test_targetes_sense_paraules_tecnices(self):
        prohibits = r'(?i)(?:5\.[1-4]|verificador oficial|franja original|heretat|sessi[óo]|R[1-8]\b|\d{4}-W\d{2})'
        for escenari in ('Validat', 'Pendent de validar', 'Falten aules'):
            for t in dades_inventades(escenari).values():
                info = text(t)
                self.assertNotRegex(' '.join(str(info[k]) for k in ('titol', 'frase', 'proposem')), prohibits)
                self.assertIn(info['etiqueta'], ('Resolt amb la proposta', 'Cal decidir', 'Per saber-ho'))
                self.assertTrue(info['titol'].endswith('?'))


def valor_fora(xifra):
    from presentacio import valor
    return valor(xifra)


if __name__ == '__main__':
    unittest.main()

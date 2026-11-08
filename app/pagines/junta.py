"""Resum de decisió per a la Junta Permanent, sobre el segon semestre."""
from html import escape
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.taules import mostra_taula
from components.vistes import estat
from errors import mostra_error
from nivell2 import junta
from nivell2.base import RESULTATS as SORTIDA

RESULTATS = SORTIDA
NOMS_PROPOSTES = junta.NOMS_PROPOSTES


def disponibles():
    noms = {p.parent.name for p in RESULTATS.glob('5.*/proposta.csv')}
    for arrel in (RESULTATS, SORTIDA):
        noms.update(p.parent.name for p in (arrel / 'junta').glob('5.*/junta.json'))
    return ['Avui'] + sorted(noms, key=lambda n: tuple(int(v) for v in n.split('.')))


def ruta_resum(nom):
    rel = Path('junta') / ('junta.json' if nom == 'Avui' else f'{nom}/junta.json')
    return next((r / rel for r in (SORTIDA, RESULTATS) if (r / rel).is_file()), SORTIDA / rel)


def llegeix(path, versio=None):
    try:
        dades = json.loads(Path(path).read_text(encoding='utf-8'))
        return dades if isinstance(dades, dict) else None
    except (OSError, ValueError):
        return None


def empremtes(nom):
    proposta = None if nom == 'Avui' else RESULTATS / nom / 'proposta.csv'
    return junta.empremtes(proposta)


def genera(nom, versio=None, versio_relax=None):
    desti = SORTIDA / 'junta'
    if nom != 'Avui':
        desti /= nom
    return junta.genera(nom, resultats=RESULTATS, sortida=desti)


def resum_valid(d):
    try:
        assert isinstance(d['excepcions'], list)
        assert isinstance(d['sessions_mogudes'], list)
        assert d['data']
        fitxes(d)
        junta.documents(d)
        return True
    except (KeyError, TypeError, ValueError, AssertionError):
        return False


def carrega(nom):
    anterior = llegeix(ruta_resum(nom))
    try:
        ref = RESULTATS / '5.2' / 'proposta.csv'
        referencia = junta.empremtes(ref) if nom in ('5.3', '5.4') and ref.is_file() else None
        if (anterior and resum_valid(anterior)
                and anterior.get('versio_resum') == junta.VERSIO_RESUM
                and anterior.get('versio_calcul') == junta.VERSIO_CALCUL
                and anterior.get('empremtes') == empremtes(nom)
                and anterior.get('empremtes_referencia') == referencia):
            return anterior
        return genera(nom)
    except Exception:
        if anterior and resum_valid(anterior):
            return dict(anterior, avis_actualitzacio=True)
        raise


def grafic_mogudes(files):
    files = sorted(files, key=lambda r: (-r.get('afectades_pct', r['franja_pct']), r['nom']))
    fig = go.Figure(go.Bar(y=[r['nom'] for r in files], x=[r['franja_pct'] for r in files],
        orientation='h', marker_color='#2a78d6',
        text=[f"{junta.percentatge(r['franja_pct'])} · {r['franja']}/{r['sessions']} classes" for r in files],
        textposition='outside', cliponaxis=False,
        hovertemplate='%{y}: %{text}<extra></extra>'))
    fig.update_layout(height=max(260, 38 * len(files) + 80),
        xaxis=dict(title='Classes que canvien de dia o hora (%)', range=[0, 130], ticksuffix=' %'),
        yaxis=dict(autorange='reversed'), margin=dict(l=0, r=120, t=10, b=45))
    return fig


def ocupacio(classes, disponibles):
    marge = disponibles - classes
    if marge < 0:
        return 'vermell', 'Falten aules', 'var(--vermell)'
    if marge == 0:
        return 'ambre', 'Sense marge', '#e8820c'
    return 'verd', 'Hi cap', 'var(--verd)'


def barra(percent, color):
    return (f'<div class="junta-barra"><i style="width:{max(0, min(100, percent)):.2f}%;'
            f'background:{color}"></i></div>')


def files_cursos(files):
    return sorted(files, key=lambda r: (-r.get('afectades_pct', r['franja_pct']), r['nom']))


def barres_cursos(files):
    return ''.join(f'<div class="junta-fila"><span>{escape(r["nom"])}</span>'
                   + barra(r.get('afectades_pct', r['franja_pct']), 'var(--blau)')
                   + f'<b>{junta.percentatge(r.get("afectades_pct", r["franja_pct"]))}</b></div>' for r in files if r.get('afectades_pct', r['franja_pct']) > 0)


def peces_fitxes(d, grau=None):
    """Presenta els recomptes del resum; no torna a calcular l’horari."""
    peces = []

    def afegeix(pregunta, resposta, comparacio, explicacio, etiqueta, boto, detall):
        color = 'ambre' if etiqueta == 'Cal decidir' else 'verd' if etiqueta == 'Resolt amb la proposta' else 'gris'
        html = ('<section class="junta-fitxa"><h3>' + escape(pregunta) + '</h3>'
                + '<div class="junta-xifra">' + escape(resposta) + '</div>'
                + ('<small>' + escape(comparacio) + '</small>' if comparacio else '')
                + '<p>' + escape(explicacio) + '</p>'
                + (f'<span class="estat gris">{escape(etiqueta)}</span>' if color == 'gris'
                   else estat({'estat': color, 'etiqueta': etiqueta})) + '</section>')
        peces.append({'html': html, 'boto': boto, 'detall': detall})

    pics = [d['pics'][t]['pitjor'] for t in ('mati', 'tarda')]
    hi_cap = all(p['classes'] <= p['aules_disponibles'] for p in pics)
    estimacio = any(p['estimacio'] for p in pics)
    comparacio = ' · '.join(f"{nom} {p['classes']} de {p['aules_disponibles']} aules"
                            for nom, p in zip(('Matí', 'Tarda'), pics))
    context = 'Avui: ' if d.get('proposta') == 'Avui' else 'Amb la proposta: '
    explicacio = ('Estimació de les aules necessàries; cal confirmar-ne l’assignació.' if estimacio else
                  'Compara les aules ocupades a l’hora més plena de cada torn amb les disponibles.')
    afegeix('Hi cabem a l’hora més plena?', 'Sí' if hi_cap else 'No', context + comparacio,
            explicacio + ' Ajuda la Junta a valorar si hi ha prou espai.',
            'Resolt amb la proposta' if hi_cap and not estimacio and d.get('proposta') != 'Avui' else 'Cal decidir',
            'Mira les aules →', 'Com ho hem calculat')

    n = len(d['excepcions'])
    comparacio = ''
    if 'fora_torn_avui' in d and 'fora_torn_proposta' in d:
        comparacio = (f"Avui {junta.numero(d['fora_torn_avui'])} → "
                      f"{junta.numero(d['fora_torn_proposta'])} amb la proposta, en total.")
    fixades = d.get('fixades_tarda', 0)
    explicacio = (f"A més, {junta.numero(fixades)} {junta.classe(fixades)} "
                  + ('fixada es queda a la tarda perquè la regla diu que no es toca. '
                     if fixades == 1 else 'fixades es queden a la tarda perquè la regla diu que no es toquen. ')
                  if fixades else '')
    if not fixades and d['fora_torn_ja_avui']:
        anteriors = d['fora_torn_ja_avui']
        explicacio += (f"{junta.numero(anteriors)} {junta.classe(anteriors)} ja es "
                       + ('fa' if anteriors == 1 else 'fan') + ' avui fora del seu torn i no es '
                       + ('toca' if anteriors == 1 else 'toquen') + '. ')
    explicacio += ('La Junta ha de valorar aquesta excepció nova.' if n == 1 else
                   'La Junta ha de valorar aquestes excepcions noves.' if n else
                   'La proposta no afegeix cap excepció de torn que la Junta hagi d’aprovar.')
    afegeix('Quantes classes queden fora del seu torn?',
            f"{junta.numero(n)} {'classe nova' if n == 1 else 'classes noves'}",
            comparacio, explicacio, 'Cal decidir' if n else 'Resolt amb la proposta',
            'Mira les excepcions →', 'Detall tècnic')

    afectat = d.get('curs_mes_afectat')
    if afectat is None:  # Compatibilitat amb els resums antics, sense inventar percentatges.
        curs = max(d['sessions_mogudes'], key=lambda r: r['franja_pct'], default=None)
        afectat = {'criteri': 'franja', 'curs': curs if curs and curs['franja_pct'] else None}
    curs, criteri = afectat.get('curs'), afectat.get('criteri', 'franja')
    if curs:
        canvi = 'de dia o hora' if criteri == 'franja' else 'd’aula'
        comparacio = (f"Avui: horari actual → amb la proposta: {junta.percentatge(curs[criteri + '_pct'])} "
                      f"de les classes canvien {canvi} ({curs[criteri]} de {curs['sessions']}).")
        explicacio = ('Les classes que canvien d’hora passen al torn que els toca. '
                      if criteri == 'franja' and curs[criteri] and curs.get('torn') == curs[criteri] else '')
        explicacio += 'Ajuda la Junta a identificar el curs que necessita més acompanyament.'
        resposta = curs['nom']
    else:
        resposta, comparacio = 'Cap', ''
        explicacio = 'Cap curs canvia de dia ni d’hora. La Junta pot valorar una proposta que conserva els horaris.'
    afegeix('Quin curs canvia més?', resposta, comparacio, explicacio, 'Per saber-ho',
            'Mira els cursos →', 'Detall per cursos')

    grau = d.get('grau_nou') if grau is None else grau
    if grau:
        n = grau['sessions_collocades']
        mogudes = grau['sessions_52_mogudes']
        explicacio = (f"{junta.numero(n)} {junta.classe(n)} "
                      + ('col·locada; ' if n == 1 else 'col·locades; ')
                      + ('cap classe de la resta no es mou.' if not mogudes else
                         f"{junta.numero(mogudes)} {junta.classe(mogudes)} de la resta "
                         + ('es mou.' if mogudes == 1 else 'es mouen.')))
        afegeix('Hi cap el grau nou de 40 places?', 'Sí' if grau['hi_cap'] else 'No',
                'Horari proposat → amb el grau nou',
                explicacio + ' Ajuda la Junta a decidir si pot ampliar l’oferta.',
                'Resolt amb la proposta' if grau['hi_cap'] else 'Cal decidir',
                'Mira el grau nou →', 'Com ho hem calculat')
    return peces


def fitxes(d, grau=None):
    return '<div class="junta-fitxes">' + ''.join(p['html'] for p in peces_fitxes(d, grau)) + '</div>'


def obre_detall(nom):
    st.session_state['junta-obrir'] = nom


ESTIL = """<style>
.junta-fitxes{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
.junta-fitxa{background:var(--targeta,#fff);border:1px solid var(--linia,#e6e5e0);border-radius:16px;padding:18px;display:flex;flex-direction:column;gap:10px;min-width:0}
.junta-fitxa h3{font-size:14px!important;margin:0;padding:0;color:var(--tinta-2)}
.junta-xifra{font-size:32px;font-weight:700;line-height:1.2}
.junta-xifra small{font-size:15px;font-weight:500}
.junta-fitxa .estat{align-self:flex-start}
.junta-fitxa .estat.gris{background:#f0f0ed;color:#555b60}
.junta-fitxa .estat.ambre,.junta-taula .estat.ambre{background:#fff1e0;color:#9a5200}
.junta-barra{height:8px;background:#eceae4;border-radius:999px;overflow:hidden}
.junta-barra i{display:block;height:100%;border-radius:999px}
.junta-fila{display:grid;grid-template-columns:minmax(0,1fr) minmax(50px,120px) 55px;gap:10px;align-items:center;font-size:14px;padding:6px 0}
.junta-taula{width:100%;border-collapse:collapse;font-size:14px}
.junta-taula td,.junta-taula th{text-align:left;padding:8px 4px;border-bottom:1px solid var(--linia,#e6e5e0)}
.st-key-junta-targetes .junta-fitxa{border:0;padding:0;background:transparent}
.st-key-junta-targetes .junta-fitxa p{font-size:14px;margin:0}
.st-key-junta-targetes .junta-xifra{font-size:28px;overflow-wrap:anywhere}
@media(max-width:900px){.st-key-junta-targetes [data-testid="stHorizontalBlock"]{flex-direction:column}.st-key-junta-targetes [data-testid="stColumn"]{width:100%!important;min-width:0!important}}
</style>"""


def grau_nou_preparat():
    """Consulta el resum existent, sense regenerar ni escriure resultats."""
    d = llegeix(ruta_resum('5.4'))
    if (d and d.get('versio_resum') == junta.VERSIO_RESUM
            and d.get('versio_calcul') == junta.VERSIO_CALCUL
            and d.get('empremtes') == empremtes('5.4')
            and d.get('empremtes_referencia') == empremtes('5.2')):
        return d.get('grau_nou')
    return None


def mostra():
    st.markdown(ESTIL, unsafe_allow_html=True)
    st.write('Aquí tens el resum per decidir si la Junta aprova l’horari proposat: una pàgina que pots descarregar en A4.')
    st.write('La conclusió resumeix la comprovació; les targetes mostren si hi ha prou aules, quines excepcions cal valorar, quin curs canvia més i, si està comprovat, si hi cap el grau nou. Els plegables permeten consultar els detalls.')
    espai_conclusio = st.container()
    opcions = disponibles()
    with st.expander('Més opcions', expanded=False):
        triada = st.selectbox('Proposta', opcions,
                             index=opcions.index('5.2') if '5.2' in opcions else len(opcions)-1,
                             format_func=lambda nom: NOMS_PROPOSTES.get(nom, nom).split(' (')[0], key='junta-proposta')
    try:
        d = carrega(triada)
        try:
            assert 'fora_torn_ja_avui' in d
            assert 'aulari' in d
            for torn in ('mati', 'tarda'):
                assert 'estimacio' in d['pics'][torn]['pitjor']
                assert all('ocupades_al_pic' in m for m in d['pics'][torn]['mides'])
            assert all('aules_assignades' in r for r in d['sessions_mogudes'])
        except (KeyError, TypeError, AssertionError):
            st.info('Resum antic: cal tornar-lo a generar.')
            return
        d = dict(d, proposta=triada)
        if d.get('avis_actualitzacio'):
            from datetime import datetime
            hora = datetime.fromisoformat(d['data']).strftime('%H:%M')
            st.warning(f"Resum de les {hora}; no s'ha pogut actualitzar")
        with espai_conclusio:
            frases = d.get('conclusio') or junta.conclusio(d)
            frase = {'VALIDA.': 'La proposta està comprovada.',
                     'VALIDA AMB RELAXACIONS DECLARADES.': 'La proposta està comprovada amb les excepcions indicades.',
                     'NO VALIDA.': 'La proposta no supera la comprovació.',
                     'INVALIDA.': 'La proposta no supera la comprovació.'}.get(frases[0], frases[0])
            st.write('Conclusió: ' + frase + ' ' + junta.titol_marge(d) + '.')
        grau = grau_nou_preparat() if triada == '5.2' else d.get('grau_nou')
        peces = peces_fitxes(d, grau)
        with st.container(key='junta-targetes'):
            for columna, peca in zip(st.columns(len(peces)), peces):
                with columna, st.container(border=True):
                    st.markdown(peca['html'], unsafe_allow_html=True)
                    st.button(peca['boto'], on_click=obre_detall, args=(peca['detall'],),
                              key='junta-boto-' + peca['detall'] + '-' + peca['boto'])
        _, html = junta.documents(d)
        st.download_button('Descarrega el resum A4', html, file_name=f'junta-{triada}.html', mime='text/html')

        obert = st.session_state.pop('junta-obrir', None)
        with st.expander('Com ho hem calculat', expanded=obert == 'Com ho hem calculat'):
            for frase in frases[1:]:
                st.write(frase)
            st.write(junta.explicacio_aulari(d))
            st.caption(junta.resum_canvis_aula(d))
            st.write(junta.explicacio_marge(d))
            if d.get('nota_pics'):
                st.caption(d['nota_pics'])
            if junta.resum_escenari(d):
                st.write(junta.resum_escenari(d))
            if grau and not d.get('grau_nou'):
                st.write(f"Grau nou: {grau['sessions_collocades']} classes col·locades; "
                         f"{grau['sessions_52_mogudes']} classes de la resta es mouen.")
            for torn, etiqueta in [('mati', 'Matí'), ('tarda', 'Tarda')]:
                pic = d['pics'][torn].get('simultani')
                if pic:
                    st.write(f"{etiqueta}: màxim de classes alhora: {pic['classes']} ({pic['hora']}).")
            st.caption(junta.EXPLICACIO_PICS)
            st.write(junta.COM_HO_HEM_CALCULAT)
            st.subheader("Aules per mida a l'hora més plena")
            torn_triat = st.radio('Torn', ['Matí', 'Tarda'], horizontal=True)
            torn = 'mati' if torn_triat == 'Matí' else 'tarda'
            files = []
            for m in d['pics'][torn]['mides']:
                n, total = m['ocupades_al_pic'], m['aules_categoria']
                color, text = ('vermell', 'Falten') if m['marge'] < 0 else ('ambre', 'Just') if m['marge'] == 0 else ('verd', 'Hi cap')
                mida = m.get('mida', str(max(1, m['minim_places'])))
                files.append(f'<tr><td>{escape(mida)}</td><td>{n} de {total}</td>'
                             f'<td>{m["demanda_acumulada"]} de {m["oferta_acumulada"]}</td><td>'
                             + estat({'estat': color, 'etiqueta': text}) + '</td></tr>')
            st.markdown('<table class="junta-taula"><thead><tr><th>Mida</th><th>Ocupades</th><th>Prou grans</th><th>Estat</th></tr></thead><tbody>'
                        + ''.join(files) + '</tbody></table>', unsafe_allow_html=True)
            st.caption('Una aula gran pot acollir un grup petit. L’estat compara les classes amb totes les aules prou grans, guardant la reserva.')
        with st.expander('Detall per cursos', expanded=obert == 'Detall per cursos'):
            st.subheader('Classes que canvien d’horari o d’aula, per curs')
            cursos = files_cursos([r for r in d.get('cursos_afectats', d['sessions_mogudes'])
                                   if r.get('afectades_pct', r['franja_pct']) > 0])
            if not cursos:
                st.write('Cap curs canvia de dia ni d’hora.')
            else:
                st.markdown(barres_cursos(cursos[:8]), unsafe_allow_html=True)
                if len(cursos) > 8:
                    with st.expander('Veure tots els cursos', expanded=False):
                        st.markdown(barres_cursos(cursos), unsafe_allow_html=True)
            if d.get('mostrar_canvis', triada != 'Avui'):
                mostra_taula(pd.DataFrame([{'Titulació i curs': r['nom'],
                    'Canvi d’hora': r['franja'], 'Canvi d’aula': r['aula'], 'Aules assignades': r['aules_assignades'],
                    'Total afectades': r.get('afectades', r['franja'])}
                    for r in files_cursos(d['sessions_mogudes'])]))
        with st.expander('Detall tècnic', expanded=obert == 'Detall tècnic'):
            st.subheader(junta.titol_marge(d))
            st.write(junta.explicacio_marge(d))
            st.write(d.get('detall_tecnic', junta.DETALL_TECNIC))
            st.caption(f"Resum calculat: {junta.data_planera(d['data'])} · {NOMS_PROPOSTES.get(triada, triada)}")
            st.caption('Les mides corresponen al moment de més ocupació del torn triat; sense aula assignada, fem servir els alumnes previstos (estimació). Els colors són orientatius i no garanteixen que tot l’horari encaixi.')
            if 'fora_torn_avui_compten' in d:
                st.write(f"Fora de torn avui: {d['fora_torn_avui_compten']} classes que compten "
                         f"i {d['fora_torn_avui_heretades']} classes fixades que es mantenen.")
            if junta.resum_guany_torn(d):
                st.write(junta.resum_guany_torn(d))
            if d.get('resum_excepcions_aula'):
                st.write(d['resum_excepcions_aula'])
            if d['torn_no_avaluable']:
                st.write(f"{d['torn_no_avaluable']} {junta.classe(d['torn_no_avaluable'])} sense torn definit.")
            if d['excepcions']:
                st.subheader('Excepcions als torns')
                st.write(junta.resum_excepcions(d))
                for motiu in dict.fromkeys(e['motiu'] for e in d['excepcions']):
                    casos = [e for e in d['excepcions'] if e['motiu'] == motiu]
                    noms = sorted({junta.nom(c) for e in casos for c in e['cohorts']})
                    st.write(f"{len(casos)} {junta.classe(len(casos))}: {junta.motiu_planer(motiu)} Titulacions: {', '.join(noms)}.")
                mostra_taula(pd.DataFrame([dict(e, motiu=junta.motiu_planer(e['motiu'])) for e in d['excepcions']]))
    except Exception:
        mostra_error()
    finally:
        st.write('Pas següent: pregunta-ho a l’Assistent (botó de baix a la dreta)')

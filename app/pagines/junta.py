"""Resum de decisió per a la Junta Permanent, sobre el segon semestre."""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.taules import mostra_taula
from components.vistes import estat
from errors import mostra_error
from nivell2 import junta
from nivell2.base import RESULTATS as SORTIDA, GRAU_NOU, Proposta
from horaris.check import Informe, _col_loca

RESULTATS = Path('/Users/bernatroca/Bernat/Hackathon/resultats/nivell2')


def disponibles():
    noms = {p.parent.name for p in RESULTATS.glob('5.*/proposta.csv')}
    for arrel in (RESULTATS, SORTIDA):
        noms.update(p.parent.name for p in (arrel / 'junta').glob('5.*/junta.json'))
    return ['Avui'] + sorted(noms, key=lambda n: tuple(int(v) for v in n.split('.')))


def ruta_resum(nom):
    rel = Path('junta') / ('junta.json' if nom == 'Avui' else f'{nom}/junta.json')
    return next((r / rel for r in (SORTIDA, RESULTATS) if (r / rel).is_file()), SORTIDA / rel)


@st.cache_data
def llegeix(path, versio):
    return json.loads(Path(path).read_text(encoding='utf-8'))


@st.cache_data
def genera(nom, versio, versio_relax):
    escenari = GRAU_NOU if nom == '5.4' else None
    base = junta.carrega_oficial(escenari)
    model = junta.carrega_model(escenari)
    if nom == 'Avui':
        proposta = Proposta.de_base(base)
        col = _col_loca(base, proposta.a_files(), Informe())
        relax = None
    else:
        path = RESULTATS / nom / 'proposta.csv'
        proposta, col = junta.carrega_proposta(path, base)
        relax = path.with_name('relaxacions.csv')
        relax = relax if relax.is_file() else None
    dades = junta.calcula(proposta, base, model, col, relax)
    desti = SORTIDA / 'junta'
    if nom != 'Avui':
        desti /= nom
    desti.mkdir(parents=True, exist_ok=True)
    (desti / 'junta.json').write_text(json.dumps(dades, ensure_ascii=False, indent=2), encoding='utf-8')
    return dades


def carrega(nom):
    path = ruta_resum(nom)
    if path.is_file():
        return llegeix(str(path), path.stat().st_mtime_ns)
    proposta = RESULTATS / nom / 'proposta.csv'
    relax = proposta.with_name('relaxacions.csv')
    return genera(nom, proposta.stat().st_mtime_ns if proposta.is_file() else 0,
                  relax.stat().st_mtime_ns if relax.is_file() else 0)


def grafic_mogudes(files):
    files = sorted(files, key=lambda r: (-r['mogudes_pct'], r['nom']))
    fig = go.Figure(go.Bar(y=[r['nom'] for r in files], x=[r['mogudes_pct'] for r in files],
        orientation='h', marker_color='#2a78d6',
        text=[f"{r['mogudes_pct']:.1f} % · {r['mogudes']}/{r['sessions']} sessions" for r in files],
        textposition='outside', cliponaxis=False,
        hovertemplate='%{y}: %{text}<extra></extra>'))
    fig.update_layout(height=max(260, 38 * len(files) + 80),
        xaxis=dict(title='Sessions mogudes (%)', range=[0, 130], ticksuffix=' %'),
        yaxis=dict(autorange='reversed'), margin=dict(l=0, r=120, t=10, b=45))
    return fig


def mostra():
    st.caption('2n semestre · Decisió sobre els torns: 1r i 2n al matí; 3r, 4t, dobles titulacions i màsters a la tarda.')
    opcions = disponibles()
    triada = st.selectbox('Proposta', opcions, index=len(opcions)-1, key='junta-proposta')
    if '5.2' not in opcions:
        st.info('El resum definitiu sortirà amb la proposta del 5.2')
    try:
        d = carrega(triada)
        st.caption(f"Resum calculat: {d['data']} · {triada}")
        st.subheader('Pic de classes alhora')
        st.caption('21 aules ordinàries menys 2 de reserva: 19 disponibles. Pitjor moment de cada torn al llarg del semestre.')
        for columna, torn, nom in zip(st.columns(2), ('mati', 'tarda'), ('Matí', 'Tarda')):
            p = d['pics'][torn]['pitjor']
            cap = p['classes'] <= p['aules_disponibles']
            with columna, st.container(border=True):
                st.markdown(estat({'estat': 'verd' if cap else 'vermell', 'etiqueta': nom + (' · Hi cap' if cap else ' · Falten aules')}), unsafe_allow_html=True)
                st.markdown(f'<div class="xifra-targeta" style="color:var(--{"verd" if cap else "vermell"}-text)">{p["classes"]} / {p["aules_disponibles"]} aules</div>', unsafe_allow_html=True)
                st.caption(f"{p['data'] or 'Sense classes'} · {p['hora']}")
        st.subheader('Aules que falten o sobren per mida')
        files = []
        for m, t in zip(d['pics']['mati']['mides'], d['pics']['tarda']['mides']):
            files.append({'Places mínimes': max(1, m['minim_places']),
                'Matí: sobren (+) o falten (−)': m['marge'], 'Tarda: sobren (+) o falten (−)': t['marge']})
        mostra_taula(pd.DataFrame(files))
        st.caption('Llindars acumulats: les aules grans també poden acollir grups petits. No sumis els marges. La reserva de dues aules és flexible; aquest recompte no garanteix que l’horari encaixi.')
        st.subheader('Sessions mogudes per titulació i curs')
        st.write('Percentatge de les seves sessions que canvien de dia, hora o aula; cada sessió compta un sol cop.')
        if all(r['mogudes_pct'] == 0 for r in d['sessions_mogudes']):
            st.write('Cap sessió moguda: totes les titulacions i cursos empaten al 0 %.')
        else:
            st.plotly_chart(grafic_mogudes(d['sessions_mogudes']), width='stretch')
            pitjors = [r for r in d['sessions_mogudes'] if r['cohort'] in d['pitjor_cohort']]
            st.write('Percentatge més alt: ' + '; '.join(f"{r['nom']}: {r['mogudes_pct']:.1f} % ({r['mogudes']} sessions)" for r in pitjors))
        st.subheader('Excepcions a la regla 1: torn requerit')
        if not d['excepcions']:
            st.write('No hi ha cap sessió fora del torn requerit.')
        else:
            motius = {}
            for r in d['excepcions']:
                motius[r['motiu']] = motius.get(r['motiu'], 0) + 1
            mostra_taula(pd.DataFrame([{'Motiu': m, 'Sessions': n} for m, n in motius.items()]))
            st.caption('L’hora acredita l’incompliment, però no demostra que sigui impossible corregir-lo.')
            with st.expander('Veure les dades'):
                mostra_taula(pd.DataFrame(d['excepcions']).rename(columns={'id_sessio': 'Sessió', 'cohorts': 'Titulació i curs (identificador)', 'torn_requerit': 'Torn requerit', 'motiu': 'Motiu', 'prova': 'Data i hora', 'prova_impossibilitat': 'Prova d’impossibilitat'}))
        if d['torn_no_avaluable']:
            st.caption(f"{d['torn_no_avaluable']} sessions sense torn definit: no es poden avaluar.")
        st.subheader('Com ho hem calculat')
        st.write(d['com_ho_hem_calculat'])
        _, html = junta.documents(d)
        st.download_button('Descarrega junta.html · A4 per imprimir', html, file_name='junta.html', mime='text/html')
        st.caption('Obre el fitxer al navegador i imprimeix-lo en PDF, mida A4.')
    except Exception:
        mostra_error()

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
        dades = llegeix(str(path), path.stat().st_mtime_ns)
        if (all('estimacio' in dades['pics'][t]['pitjor'] for t in ('mati', 'tarda'))
                and all('ocupades_al_pic' in m for t in ('mati', 'tarda')
                        for m in dades['pics'][t]['mides'])
                and all('aules_assignades' in r for r in dades['sessions_mogudes'])):
            return dades
        # Recalcula els resums antics: moviments i mides han de seguir el criteri actual.
    proposta = RESULTATS / nom / 'proposta.csv'
    relax = proposta.with_name('relaxacions.csv')
    return genera(nom, proposta.stat().st_mtime_ns if proposta.is_file() else 0,
                  relax.stat().st_mtime_ns if relax.is_file() else 0)


def grafic_mogudes(files):
    files = sorted(files, key=lambda r: (-r['franja_pct'], r['nom']))
    fig = go.Figure(go.Bar(y=[r['nom'] for r in files], x=[r['franja_pct'] for r in files],
        orientation='h', marker_color='#2a78d6',
        text=[f"{r['franja_pct']:.1f} % · {r['franja']}/{r['sessions']} classes" for r in files],
        textposition='outside', cliponaxis=False,
        hovertemplate='%{y}: %{text}<extra></extra>'))
    fig.update_layout(height=max(260, 38 * len(files) + 80),
        xaxis=dict(title='Classes que canvien de dia o hora (%)', range=[0, 130], ticksuffix=' %'),
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
        st.subheader('Moment amb més aules ocupades')
        st.caption('Mostrem quantes aules calen en el moment de més ocupació. Si falta assignar una aula, en fem una estimació.')
        st.caption('De les 21 aules per a classes, dues sempre han de quedar lliures: 19 disponibles. Mostrem el moment de més ocupació de cada torn durant el semestre.')
        for columna, torn, nom in zip(st.columns(2), ('mati', 'tarda'), ('Matí', 'Tarda')):
            p = d['pics'][torn]['pitjor']
            cap = p['classes'] <= p['aules_disponibles']
            with columna, st.container(border=True):
                st.markdown(estat({'estat': 'verd' if cap else 'vermell', 'etiqueta': nom + (' · Hi cap' if cap else ' · Falten aules')}), unsafe_allow_html=True)
                st.markdown(f'<div class="xifra-targeta" style="color:var(--{"verd" if cap else "vermell"}-text)">{p["classes"]} / {p["aules_disponibles"]} aules</div>', unsafe_allow_html=True)
                st.caption('Estimació de les aules necessàries' if p['estimacio']
                           else 'Aules ocupades en el moment de més ocupació')
                st.caption(f"{p['data'] or 'Sense classes'} · {p['hora']}")
        st.subheader('Aules que falten o sobren segons les places')
        format_actual = all('ocupades_al_pic' in m for torn in ('mati', 'tarda')
                            for m in d['pics'][torn]['mides'])
        if not format_actual:
            st.info('Resum antic: cal tornar-lo a generar per comparar les places amb el màxim d’ocupació.')
        files = []
        for m, t in zip(d['pics']['mati']['mides'], d['pics']['tarda']['mides']):
            files.append({'Places': m.get('mida', str(max(1, m['minim_places']))),
                'Matí: ocupades al màxim': m.get('ocupades_al_pic'),
                'Tarda: ocupades al màxim': t.get('ocupades_al_pic'),
                'Aules de la mida': m['aules_categoria'],
                'Matí: sobren (+) o falten (−)': m['marge'] if format_actual else None,
                'Tarda: sobren (+) o falten (−)': t['marge'] if format_actual else None})
        mostra_taula(pd.DataFrame(files))
        st.caption('Les aules ocupades per mida sumen el màxim de cada torn. La mida indica les places de l’aula; si encara no en té, indica els alumnes previstos (estimació).')
        st.caption('Comparem les classes i les aules prou grans a partir del mínim de places de cada fila. Les aules grans també poden acollir grups petits. Cal mantenir dues aules lliures. No sumis els resultats de les files. Aquest recompte no garanteix que tot l’horari encaixi.')
        st.subheader('Classes que canvien per titulació i curs')
        st.write('Percentatge de les classes que canvien de dia o d’hora; cada classe compta un sol cop.')
        if all(r['franja_pct'] == 0 for r in d['sessions_mogudes']):
            st.write('Cap classe canvia de dia ni d’hora: totes les titulacions i cursos empaten al 0 %.')
        else:
            st.plotly_chart(grafic_mogudes(d['sessions_mogudes']), width='stretch')
            pitjors = [r for r in d['sessions_mogudes'] if r['cohort'] in d['pitjor_cohort']]
            st.write('Percentatge més alt: ' + '; '.join(f"{r['nom']}: {r['franja_pct']:.1f} % ({r['franja']} classes)" for r in pitjors))
        mostra_taula(pd.DataFrame([{
            'Titulació i curs': r['nom'],
            'Canvien de dia o hora (%)': r['franja_pct'],
            'Canvien d’aula (%)': r['aula_pct'],
            'Canvis d’aula': r['aula'],
            'Aules assignades': r['aules_assignades'],
        } for r in d['sessions_mogudes']]))
        st.caption('Assignar aula a una classe que no en tenia no és un canvi d’aula.')
        st.subheader('Classes fora del torn que els toca')
        if not d['excepcions']:
            st.write('No hi ha cap classe fora del torn que li toca.')
        else:
            motius = {}
            for r in d['excepcions']:
                motius[r['motiu']] = motius.get(r['motiu'], 0) + 1
            mostra_taula(pd.DataFrame([{'Motiu': f'Motiu {i} (detall tècnic)', 'Classes': n}
                                       for i, (m, n) in enumerate(motius.items(), 1)]))
            st.caption('Sabem a quina hora es fan aquestes classes, però això no demostra que sigui impossible canviar-les.')
        if d['torn_no_avaluable']:
            st.caption(f"{d['torn_no_avaluable']} classes sense torn definit: no es poden avaluar.")
        st.subheader('Com ho hem calculat')
        st.write(junta.COM_HO_HEM_CALCULAT)
        with st.expander('Detall tècnic', expanded=False):
            st.write(d.get('detall_tecnic', junta.DETALL_TECNIC))
            if d['excepcions']:
                for i, motiu in enumerate(motius, 1):
                    st.write(f'Motiu {i}: {motiu}')
                mostra_taula(pd.DataFrame(d['excepcions']).rename(columns={
                    'id_sessio': 'Classe', 'cohorts': 'Titulació i curs (identificador)',
                    'torn_requerit': 'Torn requerit', 'motiu': 'Motiu',
                    'prova': 'Data i hora', 'prova_impossibilitat': 'Prova d’impossibilitat'}))
        if format_actual:
            _, html = junta.documents(d)
            st.download_button('Descarrega junta.html · A4 per imprimir', html, file_name='junta.html', mime='text/html')
            st.caption('Obre el fitxer al navegador i imprimeix-lo en PDF, mida A4.')
    except Exception:
        mostra_error()

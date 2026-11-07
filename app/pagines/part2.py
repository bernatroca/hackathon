"""Part 2: comparació setmanal per estudiant i lliurament per aula."""
import csv
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
from components.vistes import estat, franja_context
from components.taules import mostra_taula
from errors import mostra_error
from nivell2.base import carrega_oficial, Proposta, PAQUET, GRAU_NOU
from components.graella import (grups, setmana_tipica, dilluns, celles_grup,
    celles_aula, taula_html, exporta_aula_html, resum_grup)

RESULTATS = Path("/Users/bernatroca/Bernat/Hackathon/resultats/nivell2")


@st.cache_data
def carrega_dades(grau_nou=False):
    base = carrega_oficial(GRAU_NOU if grau_nou else None)
    with (PAQUET / 'activitats.csv').open(encoding='utf-8-sig', newline='') as f:
        noms = {r['codi']: r['assignatura'] for r in csv.DictReader(f)}
    with (PAQUET / 'plans.csv').open(encoding='utf-8-sig', newline='') as f:
        titulacions = {r['titulacions']: r['descripcio'] for r in csv.DictReader(f)}
    return base, noms, titulacions


@st.cache_data
def carrega_proposta(path, versio):
    return Proposta.llegeix(Path(path))


@st.cache_data
def carrega_relaxacions(path, versio):
    resultat = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        if not {'restriccio', 'sessions', 'justificacio'} <= set(lector.fieldnames or []):
            raise ValueError('Falten columnes al fitxer de relaxacions.')
        for r in lector:
            for sid in r['sessions'].split('|'):
                resultat.setdefault(sid.strip(), []).append(f"Excepció declarada ({r['restriccio']}): {r['justificacio']}")
    return resultat


def proposta_per_defecte(opcions):
    return next((p for p in ('5.2', '5.1') if p in opcions), 'Avui')


@st.cache_data
def carrega_excepcions(path, versio):
    resultat = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        if not {'id_sessio', 'data', 'minut_inici', 'motiu'} <= set(lector.fieldnames or []):
            raise ValueError('Falten columnes al fitxer d’excepcions.')
        for r in lector:
            data = date.fromisoformat(r['data'])
            minut = int(r['minut_inici'])
            if not 0 <= minut < 1440:
                raise ValueError('Hora incorrecta a les excepcions.')
            resultat.setdefault(r['id_sessio'], []).append(
                f"Excepció de calendari ({data:%d/%m/%Y}, {minut//60:02}:{minut%60:02}): {r['motiu']}")
    return resultat


def mostra():
    st.caption('2n semestre · Compara la setmana de l’estudiant i consulta l’horari de cada aula.')
    opcions = ['Avui'] + [n for n in ('5.1', '5.2', '5.3', '5.4') if (RESULTATS / n / 'proposta.csv').is_file()]
    triada = st.selectbox('Proposta', opcions, index=opcions.index(proposta_per_defecte(opcions)), key='p2-proposta')
    try:
        base, noms, titulacions = carrega_dades(triada == '5.4')
        avui = Proposta.de_base(base)
        relaxacions = {}
        if triada == 'Avui':
            proposta = avui
            st.info('Dades de mostra: es fa servir l’horari d’avui. Tria una proposta quan estigui disponible.')
        else:
            path = RESULTATS / triada / 'proposta.csv'
            proposta = carrega_proposta(str(path), path.stat().st_mtime_ns)
            rp = path.with_name('relaxacions.csv')
            if rp.is_file():
                relaxacions = carrega_relaxacions(str(rp), rp.stat().st_mtime_ns)
            ep = path.with_name('excepcions.csv')
            if ep.is_file():
                for sid, motius in carrega_excepcions(str(ep), ep.stat().st_mtime_ns).items():
                    relaxacions.setdefault(sid, []).extend(motius)
        tipica = setmana_tipica(base)
        setmanes = sorted({dilluns(s.data) for s in base.sessions.values()} | {date(2027, 3, 8), date(2027, 3, 15)})
        setmana = st.selectbox('Setmana de la graella', [None] + setmanes,
            format_func=lambda d: f'Setmana típica · {tipica:%d/%m/%Y}' if d is None else f'{d:%d/%m/%Y} – {d + timedelta(days=4):%d/%m/%Y}', key='p2-setmana') or tipica
        st.markdown(franja_context(2, None if st.session_state['p2-setmana'] is None else setmana, tipica), unsafe_allow_html=True)
        st.caption('La mateixa setmana a les dues graelles. Les setmanes del 8 i del 15 de març inclouen els imprevistos.')
        st.subheader('La setmana de l’estudiant')
        arbre = grups(base)
        if not arbre:
            st.info('No hi ha grups de teoria per mostrar.')
            return
        a, b, c = st.columns(3)
        tit = a.selectbox('Titulació', sorted(arbre), format_func=lambda t: titulacions.get(t, t), key='p2-titulacio')
        curs = b.selectbox('Curs', sorted(arbre[tit]), key='p2-curs')
        grup = c.selectbox('Grup de teoria', sorted(arbre[tit][curs]), key='p2-grup')
        actuals = celles_grup(base, avui, setmana, tit, curs, grup, noms=noms)
        noves = celles_grup(base, proposta, setmana, tit, curs, grup, noms=noms, relaxacions=relaxacions)
        # Inclou també les recuperacions que surten de la setmana seleccionada.
        afectades = ({c.id_sessio for c in noves if c.canvi}
            | ({c.id_sessio for c in actuals} - {c.id_sessio for c in noves}))
        n = len(afectades)
        with st.container(key='heroi'):
            st.markdown(estat({'estat': 'ambre', 'etiqueta': 'Comparació d’horaris'}), unsafe_allow_html=True)
            st.subheader(f'{n} classes amb canvis al grup')
            st.write('Canvis de dia, hora o aula respecte d’avui. Aquest recompte no és un veredicte de validació.')
        st.write(resum_grup(base, proposta, actuals, noves))
        st.caption('Groc i text: canvi de franja o aula. Vora discontínua: relaxació o excepció de calendari; passa-hi el ratolí per veure el motiu. Es conserva l’hora exacta.')
        st.markdown('<div class="comparacio-horaris">' + taula_html(actuals, 'Avui')
            + taula_html(noves, 'Proposta · ' + triada) + '</div>', unsafe_allow_html=True)
        if not actuals or not noves:
            st.info('Una de les dues graelles no té classes d’aquest grup aquesta setmana.')
        with st.expander('Veure les dades', expanded=False):
            mostra_taula(pd.DataFrame([{'id_sessio': c.id_sessio, 'dia': c.dia,
                'h_ini': f'{c.ini//60:02}:{c.ini%60:02}', 'Hora de final': f'{c.fi//60:02}:{c.fi%60:02}',
                'Assignatura': c.assignatura, 'Tipus': c.tipus, 'Grup': c.grup,
                'aula': c.aula, 'Motiu': ' '.join(c.relaxacions)} for c in noves]))
        st.subheader('La setmana per aula')
        aules = sorted(set(base.aules) | {a.aula for a in proposta.files.values() if a.aula})
        if not aules:
            st.info('No hi ha aules disponibles.')
            return
        aula = st.selectbox('Aula', aules, key='p2-aula')
        dades = celles_aula(base, proposta, setmana, aula, noms=noms, relaxacions=relaxacions)
        st.markdown(taula_html(dades, 'Aula ' + aula), unsafe_allow_html=True)
        if not dades:
            st.info('Aquesta aula no té classes assignades aquesta setmana.')
        st.download_button('Descarrega l’horari de l’aula per al jurat',
            exporta_aula_html(base, proposta, setmana, aula, noms=noms, relaxacions=relaxacions),
            file_name=f'horari-{aula.replace("/", "-")}-{setmana}.html', mime='text/html')
    except Exception:
        mostra_error()

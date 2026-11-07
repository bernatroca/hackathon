"""Part 2: comparació setmanal per estudiant i lliurament per aula."""
import csv
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from nivell2.base import carrega_oficial, Proposta, RESULTATS, PAQUET, GRAU_NOU
from components.graella import (grups, setmana_tipica, dilluns, celles_grup,
    celles_aula, taula_html, exporta_aula_html)


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


def mostra():
    st.caption('2n semestre · Compara la setmana de l’estudiant i consulta l’horari de cada aula.')
    opcions = ['Avui'] + [n for n in ('5.1', '5.2', '5.3', '5.4') if (RESULTATS / n / 'proposta.csv').is_file()]
    triada = st.selectbox('Proposta', opcions, key='p2-proposta')
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
        tipica = setmana_tipica(base)
        setmanes = sorted({dilluns(s.data) for s in base.sessions.values()} | {date(2027, 3, 8), date(2027, 3, 15)})
        setmana = st.selectbox('Setmana de la graella', [None] + setmanes,
            format_func=lambda d: f'Setmana típica · {tipica:%d/%m/%Y}' if d is None else f'{d:%d/%m/%Y} – {d + timedelta(days=4):%d/%m/%Y}', key='p2-setmana') or tipica
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
            st.markdown('<span class="estat ambre">! Comparació d’horaris</span>', unsafe_allow_html=True)
            st.subheader(f'{n} classes amb canvis al grup')
            st.write('Canvis de dia, hora o aula respecte d’avui. Aquest recompte no és un veredicte de validació.')
        st.caption('Groc i text: canvi de franja o aula. Vora discontínua: excepció declarada amb el motiu. Cada classe es repeteix a les franges que ocupa; es conserva l’hora exacta.')
        for col, dades, titol in zip(st.columns(2), (actuals, noves), ('Avui', 'Proposta · ' + triada)):
            with col:
                st.markdown(taula_html(dades, titol), unsafe_allow_html=True)
                if not dades:
                    st.info('No hi ha classes d’aquest grup aquesta setmana.')
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
    except (OSError, ValueError, KeyError) as exc:
        st.error(f'No s’ha pogut mostrar l’horari: {exc}')

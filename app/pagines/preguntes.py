import streamlit as st
from components.vistes import detall_obert, targeta_compacta, contingut, estil_respostes
from presentacio import ordena_respostes, grup_estat
from servei import totes
from errors import mostra_error

ESTATS = ['Cal actuar', 'Vigilar', 'Hi cap']


def mostra():
    try:
        resultat = totes(st.session_state.semestre, st.session_state.setmana, st.session_state.versio)
        st.session_state.resultats = {t.id:t for t in resultat}
    except Exception:
        mostra_error()
        return
    if detall_obert():
        return
    st.write('Les respostes més urgents primer. Obre’n una per veure el detall i les possibles millores.')
    if not resultat:
        st.info('Les respostes encara no estan disponibles.')
        return
    infos = {t.id:contingut(t) for t in resultat}
    resultat = ordena_respostes(resultat, infos)
    ambits = {t.id:t for t in resultat}
    with st.container(key='respostes'):
        estil_respostes()
        with st.container(key='filtres-respostes'):
            estat_col, respostes_col, recompte_col = st.columns([2.2, 2.2, 1.2])
            with estat_col:
                estats = st.pills('Estat', ESTATS, selection_mode='multi', default=ESTATS,
                    key='respostes-estat', help='«Vigilar» inclou les respostes pendents de validar.')
            with respostes_col:
                triades = st.multiselect('Respostes', list(ambits),
                    format_func=lambda id_:infos[id_]['titol'], default=[],
                    placeholder='Totes les respostes', key='respostes-triades')
            visibles = [t for t in resultat if grup_estat(infos[t.id]) in estats
                        and (not triades or t.id in triades)]
            with recompte_col:
                st.markdown(f'<p class="recompte" role="status">Es mostren {len(visibles)} de {len(resultat)}</p>',unsafe_allow_html=True)
        if not visibles:
            st.info('Cap resposta coincideix amb els filtres. Canvia «Estat» o buida «Respostes».')
            return
        with st.container(key='graella-respostes'):
            columnes = st.columns(len(visibles))
            for columna,t in zip(columnes,visibles):
                with columna:
                    targeta_compacta(t,infos[t.id])

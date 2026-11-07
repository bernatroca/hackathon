import streamlit as st
from components.vistes import detall_obert, targeta
from servei import totes


def mostra():
    try:
        resultat = totes(st.session_state.semestre, st.session_state.setmana, st.session_state.versio)
        st.session_state.resultats = {t.id:t for t in resultat}
    except Exception as exc:
        st.error(f'No s’han pogut carregar les respostes: {exc}')
        return
    if detall_obert():
        return
    st.write('Una resposta i una proposta per a cada pregunta sobre els espais.')
    resultat = list(st.session_state.get('resultats',{}).values())
    if not resultat:
        st.info('Les respostes encara no estan disponibles.')
        return
    with st.container(key='targetes'):
        columnes = st.columns(len(resultat))
        for posicio,(columna,t) in enumerate(zip(columnes,resultat)):
            with columna:
                targeta(t,posicio)

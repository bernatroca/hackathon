import streamlit as st
from components.vistes import detall_obert, targeta


def mostra():
    if detall_obert():
        return
    st.title('Totes les respostes')
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

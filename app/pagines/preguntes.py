import streamlit as st
from components.vistes import detall
from servei import totes


def mostra():
    st.title('Totes les preguntes')
    st.caption('Troballes reals disponibles al registre, sense dades de mostra.')
    try:
        resultat = totes(st.session_state.semestre, st.session_state.setmana, st.session_state.versio)
    except Exception as exc:
        st.error(f'No s’han pogut carregar les preguntes: {exc}')
        return
    if not resultat:
        st.info('Aviat · Els mòduls de preguntes encara no són al registre.')
        return
    ids = [t.id for t in resultat]
    titols = {t.id: t.titol for t in resultat}
    id_ = st.selectbox('Pregunta', ids, format_func=titols.get)
    detall(next(t for t in resultat if t.id == id_))

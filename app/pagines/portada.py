import streamlit as st
from nivell1.troballes import PORTADA
from components.vistes import carrega, carrega_grup, detall_obert, heroi, targeta, estat


def mostra():
    carrega_grup(PORTADA)
    if detall_obert():
        return
    st.markdown(' '.join(estat(dict(estat=color, etiqueta=nom)) for color,nom in
        [('verd','Tot bé'),('ambre','Vigilar'),('vermell','Cal actuar')]), unsafe_allow_html=True)
    st.caption('Classes fora de torn, sense aula i altres problemes: tot el semestre. El matí i el grau nou: la setmana indicada a cada detall. Pots canviar-la a «Opcions».')
    t = carrega('hi-cap-mati')
    if t is not None:
        heroi(t)
    altres = [id_ for id_ in PORTADA if id_ != 'hi-cap-mati']
    with st.container(key='targetes'):
        columnes = st.columns(len(altres))
        for posicio,(columna,id_) in enumerate(zip(columnes,altres)):
            with columna:
                t = carrega(id_)
                if t is not None:
                    targeta(t,posicio)

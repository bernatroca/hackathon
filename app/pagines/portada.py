import streamlit as st
from nivell1.troballes import PORTADA
from components.vistes import carrega, carrega_grup, detall_obert, heroi, targeta


def mostra():
    carrega_grup(PORTADA)
    if detall_obert():
        return
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

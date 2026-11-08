import streamlit as st
from nivell1.troballes import PORTADA
from components.vistes import carrega, carrega_grup, detall_obert, heroi, targeta, pas_seguent


def mostra():
    st.write('Aquí veus com s’utilitzen avui les aules. Comença pel bloc gran i obre «Com ho sabem» per entendre cada resposta.')
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
    pas_seguent()

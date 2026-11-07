import streamlit as st
from nivell1.troballes import PORTADA
from components.vistes import carrega, detall, targeta


def mostra():
    id_ = st.session_state.get('detall_id')
    if id_:
        if st.button('← Torna a les troballes'):
            st.session_state.detall_id = None
            st.rerun()
        detall(carrega(id_))
        return
    st.title('Troballes')
    st.write('On van plens els espais i hi cap el model nou?')
    st.caption('Escola d’Enginyeria · UAB · Planificació del curs 2027–28')
    for inici in range(0, len(PORTADA), 3):
        columnes = st.columns(min(3, len(PORTADA) - inici), gap='large')
        for posicio, (columna, id_) in enumerate(zip(columnes, PORTADA[inici:inici + 3]), inici):
            with columna:
                t = carrega(id_)
                if t is not None:
                    targeta(t, posicio)

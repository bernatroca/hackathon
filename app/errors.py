"""Missatge públic únic per renderitzat, sense dades privades al registre."""
import logging
import streamlit as st

MISSATGE = 'No hem pogut carregar les dades. Prem «Torna-ho a provar». Si continua passant, avisa l’equip.'


def mostra_error():
    if st.session_state.get('_error_mostrat', False):
        return
    st.session_state['_error_mostrat'] = True
    # Els errors de lectura poden contenir dades privades: no registrem la traça.
    logging.getLogger('espais.part1').error('Error carregant les dades de la part 1')
    missatge, boto = st.columns([4, 1])
    missatge.error(MISSATGE)
    if boto.button('Torna-ho a provar', key='reintenta-dades'):
        from servei import actualitza_dades
        actualitza_dades()
        st.rerun()

"""Missatge públic únic; els detalls es conserven només al registre local."""
import logging
import streamlit as st

MISSATGE = 'No hem pogut carregar les dades. Prem "Actualitza les dades". Si continua passant, avisa l’equip.'


def mostra_error():
    logging.getLogger('espais.part1').exception('Error carregant les dades de la part 1')
    st.error(MISSATGE)

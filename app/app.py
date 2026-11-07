"""Executa amb: streamlit run app/app.py."""
import sys
from pathlib import Path

# Tant Streamlit com AppTest han de trobar l'esquelet del repositori.
ARREL = Path(__file__).resolve().parent
for carpeta in (ARREL.parent, ARREL):
    if str(carpeta) not in sys.path:
        sys.path.insert(0, str(carpeta))

import streamlit as st
from components.vistes import carrega, detall
from pagines import portada, preguntes
from servei import setmanes, versio_registre

st.set_page_config(page_title='Espais UAB · Troballes', page_icon='▦', layout='wide')
st.markdown('''<style>
.stApp {background-color:#FAFCFC;color:#24383D;}
.block-container {padding-top:2.8rem;padding-bottom:3rem;max-width:1450px;}
[data-testid="stMetricValue"] {font-size:2.7rem;color:#28666E;}
[data-testid="stMetricLabel"] {white-space:normal;}
h1,h2,h3 {letter-spacing:-.025em;}
</style>''', unsafe_allow_html=True)
with st.sidebar:
    st.title('Espais UAB')
    st.caption('Part 1 · Anàlisi dels espais')
    semestre = st.selectbox('Semestre', [2, 1], format_func=lambda s: '1r' if s == 1 else '2n', key='semestre')
    try:
        disponibles = setmanes(semestre)
    except Exception as exc:
        disponibles = []
        st.error(f'No s’han pogut llegir les setmanes: {exc}')
    setmana = st.selectbox('Setmana', [None] + disponibles,
        format_func=lambda s: 'Típica' if s is None else str(s), key=f'setmana-{semestre}')
    st.session_state.setmana = setmana
    st.caption('«Típica» delega la setmana de referència al mòdul de dades. «Hi cap el matí?» aplica la pitjor setmana segons el seu mètode.')
    if st.button('Actualitza les dades'):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption('Ús local · Les dades no es publiquen')
st.session_state.versio = versio_registre()


def mapa():
    detall(carrega('ocupacio'))


def mati():
    detall(carrega('hi-cap-mati'))


def proposta():
    st.title('Part 2 · Proposta d’horari')
    st.info('Aviat · Generació de la proposta d’horari.')


def assistent():
    st.title('Part 3 · Assistent')
    st.info('Aviat · Assistent per explorar els horaris i els espais.')


pagina = st.navigation({
    'Part 1 · Anàlisi': [st.Page(portada.mostra, title='Troballes', url_path='troballes', default=True),
        st.Page(mapa, title='Mapa de calor'), st.Page(mati, title='Hi cap el matí?'),
        st.Page(preguntes.mostra, title='Totes les preguntes', url_path='preguntes')],
    'Properament': [st.Page(proposta, title='Part 2 · Proposta d’horari'), st.Page(assistent, title='Part 3 · Assistent')],
})
pagina.run()

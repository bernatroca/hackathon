"""Executa amb streamlit run app/app.py des de l'arrel del repositori."""
import sys
from pathlib import Path
ARREL = Path(__file__).resolve().parent
for carpeta in (ARREL.parent,ARREL):
    if str(carpeta) not in sys.path:
        sys.path.insert(0,str(carpeta))

import streamlit as st
from pagines import portada, preguntes
from servei import setmanes, totes, versio_registre

st.set_page_config(page_title="Espais de l’Escola",page_icon='▦',layout='wide')
st.markdown('<style>'+ (ARREL/'estil.css').read_text() +'</style>',unsafe_allow_html=True)
with st.sidebar:
    st.title('Espais de l’Escola')
    with st.expander('Opcions',expanded=False):
        semestre = st.selectbox('Semestre',[2,1],format_func=lambda s:'2n' if s == 2 else '1r',key='semestre')
        try:
            disponibles = setmanes(semestre)
        except Exception as exc:
            disponibles = []
            st.error(f'No s’han pogut llegir les setmanes: {exc}')
        setmana = st.selectbox('Setmana',[None]+disponibles,format_func=lambda s:'Típica' if s is None else str(s),key=f'setmana-{semestre}')
        st.session_state.setmana = setmana
        st.caption('Setmana típica: la que té un nombre de classes normal. «Hi cap el matí?» fa servir la setmana més plena si no en tries cap.')
        if st.button('Actualitza les dades'):
            st.cache_data.clear()
            st.rerun()
    st.caption('Ús local · Les dades no es publiquen')
st.session_state.versio = versio_registre()
try:
    resultat = totes(semestre,setmana,st.session_state.versio)
    st.session_state.resultats = {t.id:t for t in resultat}
except Exception as exc:
    st.session_state.resultats = {}
    st.error(f'No s’han pogut carregar les respostes: {exc}')


def canvia_pagina():
    st.session_state.detall_id = None


def proposta():
    st.title('Proposta d’horari')
    st.info('Aviat · Una proposta per repartir les classes i assignar les aules.')


def imprevistos():
    st.title('Imprevistos')
    st.info('Aviat · Reorganitza les classes quan hi hagi un canvi d’última hora.')


def pregunta():
    st.title('Pregunta-ho')
    st.info('Aviat · Fes preguntes sobre les aules i els horaris amb les teves paraules.')


pagina = st.navigation([
    st.Page(portada.mostra,title='Com estem avui',url_path='avui',default=True),
    st.Page(preguntes.mostra,title='Totes les respostes',url_path='respostes'),
    st.Page(proposta,title='Proposta d’horari · aviat'),
    st.Page(imprevistos,title='Imprevistos · aviat'),
    st.Page(pregunta,title='Pregunta-ho · aviat'),
])
# En canviar de secció del menú es torna a la llista corresponent.
if st.session_state.get('pagina_anterior') != pagina.url_path:
    canvia_pagina()
st.session_state.pagina_anterior = pagina.url_path
pagina.run()

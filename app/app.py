"""Executa amb streamlit run app/app.py des de l'arrel del repositori."""
import sys
import os
from pathlib import Path
ARREL = Path(__file__).resolve().parent
for carpeta in (ARREL.parent,ARREL):
    if str(carpeta) not in sys.path:
        sys.path.insert(0,str(carpeta))

import streamlit as st

st.set_page_config(page_title="Espais de l’Escola",page_icon='▦',layout='wide')
st.session_state['_error_mostrat'] = False
repte = Path(os.environ.get('REPTE_DIR') or ARREL.parent / 'repte' / 'repte-horaris-escola')
if not (repte / 'paquet' / 'sessions.csv').is_file() or not (repte / 'horaris').is_dir():
    missatge, boto = st.columns([4, 1])
    missatge.error('No trobem les dades del repte. Posa el paquet a repte/repte-horaris-escola/ '
                   'o indica la carpeta amb REPTE_DIR.')
    if boto.button('Torna-ho a provar', key='reintenta-paquet'):
        from nivell1.dades import connexio
        connexio.cache_clear()
        st.cache_data.clear()
        st.rerun()
    st.stop()

from pagines import portada, preguntes, part2, junta
from servei import setmanes, versio_registre, actualitza_dades
from components.vistes import franja_context
from errors import mostra_error
from xat.widget import posa_widget, pantalla_actual

st.markdown('<style>'+ (ARREL/'estil.css').read_text() +'</style>',unsafe_allow_html=True)


def proposta():
    st.info('Aviat · Una proposta per repartir les classes i assignar les aules.')


# La navegació i la capçalera s'envien abans de qualsevol lectura de dades.
pagina = st.navigation({
    'Com està l’horari': [
        st.Page(portada.mostra,title='Com estem avui',url_path='avui',default=True,icon=':material/dashboard:'),
        st.Page(preguntes.mostra,title='Totes les respostes',url_path='respostes',icon=':material/list_alt:'),
    ],
    'La proposta': [
        st.Page(part2.mostra,title='Horari proposat',url_path='part2',icon=':material/calendar_month:'),
        st.Page(junta.mostra,title='Resum per a la Junta',url_path='junta',icon=':material/description:'),
        st.Page('pagines/imprevistos.py',title='Imprevistos',url_path='imprevistos',icon=':material/event_busy:'),
    ],
})
st.session_state['_pagina_horari'] = st.Page(part2.mostra, title='Horari proposat', url_path='part2')
with st.sidebar:
    st.markdown('<div class="marca-escola">Espais de l’Escola</div>', unsafe_allow_html=True)
st.title(pagina.title)
franja = st.empty() if pagina.url_path in ('', 'avui', 'respostes') else None
if st.session_state.get('pagina_anterior') != pagina.url_path:
    st.session_state.detall_id = None
st.session_state.pagina_anterior = pagina.url_path
if pagina.url_path in ('', 'avui', 'respostes'):
    st.session_state.detall_id = st.query_params.get('resposta') or st.session_state.get('detall_id')
st.session_state.versio = versio_registre()
# Les còpies de session_state només pertanyen a aquest renderitzat. La memòria
# cau de cada troballa és qui reutilitza els resultats entre visites i filtres.
st.session_state.resultats = {}
zona = st.empty()
zona.empty()
with zona.container():
    with st.spinner('Calculant les xifres del semestre…'):
        error_setmanes = False
        with st.sidebar:
            if pagina.url_path in ('', 'avui', 'respostes'):
                with st.expander('Opcions',expanded=False):
                    semestre_desat = st.session_state.get('semestre_triat', 2)
                    semestre = st.selectbox('Semestre',[2,1], index=[2,1].index(semestre_desat),
                        format_func=lambda s:'2n' if s == 2 else '1r', key='_selector_semestre')
                    if semestre != semestre_desat:
                        st.session_state.setmana_triada = None
                    st.session_state.semestre_triat = semestre
                    st.session_state.semestre = semestre
                    try:
                        disponibles = setmanes(semestre)
                    except Exception:
                        disponibles = []
                        error_setmanes = True
                    mesos = ('gener', 'febrer', 'març', 'abril', 'maig', 'juny',
                             'juliol', 'agost', 'setembre', 'octubre', 'novembre', 'desembre')
                    etiquetes = {codi: f'Setmana del {dilluns.day} '
                                 + ('d’' if dilluns.month in (4, 8, 10) else 'de ')
                                 + f'{mesos[dilluns.month - 1]} · {n} classes'
                                 for codi, dilluns, n in disponibles}
                    opcions_setmana = [None] + list(etiquetes)
                    setmana_desada = st.session_state.get('setmana_triada')
                    setmana = st.selectbox('Setmana', opcions_setmana,
                        index=opcions_setmana.index(setmana_desada) if setmana_desada in opcions_setmana else 0,
                        format_func=lambda s:'Típica' if s is None else etiquetes[s], key=f'setmana-{semestre}')
                    if not error_setmanes:
                        st.session_state.setmana_triada = setmana
                    st.session_state.setmana = setmana
                    st.caption('Setmana típica: la que té un nombre de classes normal, sense les setmanes de menys de 200 classes. '
                               '«Hi cap el matí?» fa servir la setmana amb més classes alhora si no en tries cap.')
            else:
                semestre, setmana = 2, None
                st.caption('La proposta és del 2n semestre')
            if st.button('Actualitza les dades'):
                actualitza_dades()
                st.rerun()
            st.caption('Ús local · Les dades no es publiquen')
        if error_setmanes:
            mostra_error()
        if franja is not None:
            franja.markdown(franja_context(semestre, setmana), unsafe_allow_html=True)
        pagina.run()
        if franja is not None:
            referencia = st.session_state.resultats.get('hores-aula') or st.session_state.resultats.get('ocupacio')
            tipica = (referencia.extra or {}).get('setmana') if referencia else None
            franja.markdown(franja_context(semestre, setmana, tipica), unsafe_allow_html=True)

posa_widget(pantalla_actual(pagina.title, st.session_state))

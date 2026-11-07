"""Executa amb streamlit run app/app.py des de l'arrel del repositori."""
import sys
from pathlib import Path
ARREL = Path(__file__).resolve().parent
for carpeta in (ARREL.parent,ARREL):
    if str(carpeta) not in sys.path:
        sys.path.insert(0,str(carpeta))

import streamlit as st
from pagines import portada, preguntes, part2, junta
from servei import setmanes, versio_registre
from components.vistes import franja_context
from errors import mostra_error

st.set_page_config(page_title="Espais de l’Escola",page_icon='▦',layout='wide')
st.markdown('<style>'+ (ARREL/'estil.css').read_text() +'</style>',unsafe_allow_html=True)


def proposta():
    st.info('Aviat · Una proposta per repartir les classes i assignar les aules.')


def pregunta():
    st.info('Aviat · Fes preguntes sobre les aules i els horaris amb les teves paraules.')


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
    'Ajuda': [st.Page(pregunta,title='Pregunta-ho · aviat',icon=':material/chat:')],
})
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
        with st.sidebar:
            with st.expander('Opcions',expanded=False):
                semestre = st.selectbox('Semestre',[2,1],format_func=lambda s:'2n' if s == 2 else '1r',key='semestre')
                try:
                    disponibles = setmanes(semestre)
                except Exception as exc:
                    disponibles = []
                    mostra_error()
                setmana = st.selectbox('Setmana',[None]+disponibles,format_func=lambda s:'Típica' if s is None else str(s),key=f'setmana-{semestre}')
                st.session_state.setmana = setmana
                st.caption('Setmana típica: la que té un nombre de classes normal. «Hi cap el matí?» fa servir la setmana més plena si no en tries cap.')
                if st.button('Actualitza les dades'):
                    st.cache_data.clear()
                    st.rerun()
            st.caption('Ús local · Les dades no es publiquen')
        if franja is not None:
            franja.markdown(franja_context(semestre, setmana), unsafe_allow_html=True)
        pagina.run()
        if franja is not None:
            referencia = st.session_state.resultats.get('hores-aula') or st.session_state.resultats.get('ocupacio')
            tipica = (referencia.extra or {}).get('setmana') if referencia else None
            franja.markdown(franja_context(semestre, setmana, tipica), unsafe_allow_html=True)

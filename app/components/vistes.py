import streamlit as st
from components.grafics import grafics, numero
from mostra import exemples
from servei import una


def carrega(id_):
    try:
        return una(id_, st.session_state.semestre, st.session_state.setmana, st.session_state.versio)
    except KeyError as exc:
        # Només l'absència de l'ID al registre activa la mostra.
        if exc.args != (id_,):
            st.error(f'Error de dades a «{id_}»: {exc}')
            return None
        return exemples().get(id_)
    except Exception as exc:
        st.error(f'No s’ha pogut carregar «{id_}»: {exc}')
        return None


def detall(t):
    if t is None:
        st.info('Aquesta troballa encara no està disponible.')
        return
    st.title(t.titol)
    if (t.extra or {}).get('mostra'):
        st.warning('MOSTRA · Dades fictícies. No les feu servir per defensar resultats del repte.')
    st.metric('Xifra principal', numero(t.xifra))
    st.write(t.frase)
    grafics(t, clau='detall-' + t.id)
    st.subheader('Com s’ha calculat')
    st.write(t.metode)
    with st.expander('Consulta SQL i sessions d’exemple'):
        st.code(t.sql, language='sql')
        st.caption('id_sessio d’exemple per buscar al CSV original')
        if t.exemples:
            st.code('\n'.join(map(str, t.exemples)), language=None)
        else:
            st.write('No s’han facilitat sessions d’exemple.')


def targeta(t, posicio):
    with st.container(border=True):
        if (t.extra or {}).get('mostra'):
            st.caption('MOSTRA · dades fictícies')
        st.metric(t.titol, numero(t.xifra))
        st.write(t.frase)
        grafics(t, petit=True, clau=f'targeta-{posicio}-{t.id}')
        if st.button('Obre la troballa', key='obre-' + t.id, width='stretch'):
            st.session_state.detall_id = t.id
            st.rerun()

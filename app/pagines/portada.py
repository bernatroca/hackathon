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
    troballes = [carrega(id_) for id_ in PORTADA]
    abasts = []
    for t in troballes:
        if t is None:
            continue
        if (t.extra or {}).get('mostra'):
            abast = 'MOSTRA, sense setmana real'
        elif t.id in ('fora-torn', 'hores-aula'):
            abast = 'tot el semestre'
        else:
            setmana = (t.extra or {}).get('setmana')
            abast = f'setmana {setmana}' if setmana is not None else 'setmana no indicada pel resultat'
        abasts.append(f'{t.titol}: {abast}')
    st.caption('Abast de cada xifra · ' + ' · '.join(abasts))
    with st.container(key='targetes-portada'):
        columnes = st.columns(len(PORTADA), gap='large')
        for posicio, (columna, t) in enumerate(zip(columnes, troballes)):
            with columna:
                if t is not None:
                    targeta(t, posicio)

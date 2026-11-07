from html import escape
import streamlit as st
from components.grafics import grafics, quadrets
from mostra import exemples
from presentacio import text, abast, desglos, valor
from servei import una
from textos import PROBLEMES


def carrega(id_):
    resultat = st.session_state.get('resultats', {})
    if id_ in resultat:
        return resultat[id_]
    try:
        return una(id_, st.session_state.semestre, st.session_state.setmana, st.session_state.versio)
    except KeyError as exc:
        if exc.args != (id_,):
            st.error(f'Error de dades a «{id_}»: {exc}')
            return None
        return exemples().get(id_)
    except Exception as exc:
        st.error(f'No s’ha pogut carregar «{id_}»: {exc}')
        return None


def contingut(t):
    return text(t, st.session_state.get('resultats', {}))


def estat(info):
    icona = {'vermell':'✕','ambre':'!','verd':'✓'}[info['estat']]
    return f'<span class="estat {info["estat"]}">{icona} {escape(info["etiqueta"])}</span>'


def mostra_avis(t):
    if (t.extra or {}).get('mostra'):
        st.warning('MOSTRA · Dades fictícies; no són resultats del repte.')


def obre(t):
    if st.button('Com ho sabem →',key='obre-'+t.id):
        st.session_state.detall_id = t.id
        st.rerun()


def heroi(t):
    info = contingut(t)
    with st.container(key='heroi'):
        mostra_avis(t)
        esquerra,dreta = st.columns([3,1],gap='large')
        with esquerra:
            st.markdown(estat(info),unsafe_allow_html=True)
            st.markdown(f'<p class="pregunta">{escape(info["titol"])}</p>',unsafe_allow_html=True)
            st.subheader(info['c']['resposta'])
            st.write(info['frase'])
            if info['c'].get('coll_ampolla'):
                st.write(info['c']['coll_ampolla'])
            obre(t)
        with dreta:
            quadrets(t)
        st.caption(abast(t))
        st.caption('El recompte orienta sobre l’espai necessari; cal validar que les classes es poden repartir en un horari.')


def targeta(t, posicio=0):
    info = contingut(t)
    with st.container(border=True, key='targeta-'+t.id):
        mostra_avis(t)
        percent = info['c'].get('percent')
        metre = ''
        if percent is not None:
            metre = f'<div class="metre" role="img" aria-label="{percent:.1f} %"><i style="width:{max(0,min(100,percent)):.2f}%;background:var(--blau)"></i></div>'
        detall_desglos = desglos(t.extra) if t.id == 'hores-aula' else ''
        st.markdown(f'<article class="targeta-cor">{estat(info)}<h3>{escape(info["titol"])}</h3>'
            f'<div class="xifra-targeta">{escape(info["c"]["xifra"])}</div>'
            f'<p class="desglos">{escape(detall_desglos)}</p>{metre}<p>{escape(info["frase"])}</p>'
            f'<div class="proposem"><b>Proposem:</b> {escape(info["proposem"])}</div></article>',unsafe_allow_html=True)
        obre(t)


def detall(t):
    if t is None:
        st.info('Aquesta resposta encara no està disponible.')
        return
    info = contingut(t)
    mostra_avis(t)
    st.markdown(estat(info),unsafe_allow_html=True)
    st.title(info['titol'])
    resposta = info['c'].get('resposta',info['c']['xifra'])
    st.markdown(f'<div class="xifra-targeta resposta-gran">{escape(resposta)}</div>',unsafe_allow_html=True)
    st.caption(abast(t) + ' · La xifra principal resumeix el semestre; la comparació mostra la setmana seleccionada.'
               if t.id != 'marge-grau-nou' else abast(t) + ' · Hores necessàries i lliures en aquesta setmana.')
    grafics(t,clau='detall-'+t.id,altres=st.session_state.get('resultats',{}))
    st.subheader('Què vol dir')
    st.write(info['frase'])
    st.subheader('Proposem')
    st.write(info['proposem'])
    if t.id == 'problemes-millores' and {'problema','proposta'}.issubset(t.taula.columns):
        for fila in t.taula.itertuples():
            nom = PROBLEMES.get(fila.problema, fila.problema)
            proposta = fila.proposta.replace('una única finestra completa', 'el torn que li correspon')
            n = valor(fila.xifra)
            compte = ('1 cas' if n == 1 else f'{fila.xifra} casos') if n is not None else 'Recomanació sense recompte'
            st.markdown(f'**{nom} · {compte}**: {proposta}')
        st.caption('El gràfic mostra com a màxim les vuit categories amb més casos de la setmana. La llista inclou també la resta i les recomanacions sense recompte; les categories poden coincidir en una mateixa classe.')
    st.subheader('Com ho hem calculat')
    st.write(info.get('metode_planer', 'Consulta les definicions detallades al desplegable tècnic.'))
    with st.expander('Per a tècnics: consulta SQL i sessions d’exemple',expanded=False):
        st.write(t.metode)
        st.code(t.sql,language='sql')
        st.caption('id_sessio per buscar al CSV original')
        if len(t.exemples):
            st.code('\n'.join(map(str,t.exemples)),language=None)
        else:
            st.write('No s’han facilitat sessions d’exemple.')


def detall_obert():
    id_ = st.session_state.get('detall_id')
    if not id_:
        return False
    if st.button('← Torna a les respostes',key='torna'):
        st.session_state.detall_id = None
        st.rerun()
    detall(carrega(id_))
    return True

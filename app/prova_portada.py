"""Portada sense dades reals: streamlit run app/prova_portada.py."""
from pathlib import Path
import sys

ARREL = Path(__file__).resolve().parent
for carpeta in (ARREL.parent, ARREL):
    if str(carpeta) not in sys.path:
        sys.path.insert(0, str(carpeta))

import pandas as pd
from nivell1.troballes import Troballa


def dades_inventades(escenari='Validat'):
    """Resultats escrits a mà: no consulta fitxers, serveis ni dades del repte."""
    def resultat(id_, xifra, taula, extra=None):
        return Troballa(id_, 'Pregunta inventada', xifra, 'Resum inventat.',
            'MOSTRA: resultats inventats per comprovar la presentació.',
            '-- MOSTRA: no s’ha executat cap consulta.', pd.DataFrame(taula), extra=extra or {})

    pic = pd.DataFrame({'dia':list('LMXJV'), 'classes':[8, 12, 10, 9, 7]})
    resultats = [
        resultat('hi-cap-mati', '12 aules', pic, dict(pic=pic, setmana='2027-W07',
            ocupacio=[{'ocupacio_pct':63.2}], falla_per_mida=False,
            validat_part2={'valida':True})),
        resultat('fora-torn', '84', {'cohort':['GXX:1r'], 'sessions':[84]}),
        resultat('hores-aula', '35 %', {'dia':list('LMXJV'), 'demanda':[6, 8, 7, 5, 4],
            'sessions_totals':[120]*5}, dict(sessions_sense_aula=42,
            desglos={'per_assignar':30, 'laboratoris':8, 'dobles':4}, setmana='2027-W07')),
        resultat('marge-grau-nou', '27 h', [{'llindar':0, 'seminaris':False,
            'nou_hores':27., 'marge_hores':173.}], dict(setmana='2027-W06', criteri_setmana='demanda_mati',
            demanda_h_setmana=27., lliures_h_setmana=173.,
            cap_per_mida=True, validat_part2={'valida':True, 'resposta':1,
                'sessions_grau_nou_collocades':72, 'sessions_52_mogudes':0})),
        resultat('problemes-millores', '24', {'problema':['Sessions sense aula'],
            'xifra':[24], 'proposta':['Revisar les assignacions inventades.']}),
    ]
    mapa = {t.id:t for t in resultats}
    if escenari == 'Pendent de validar':
        for id_ in ('hi-cap-mati', 'marge-grau-nou'):
            mapa[id_].extra['validat_part2'] = None
    elif escenari == 'Falten aules':
        mapa['hi-cap-mati'].extra.update(falla_per_mida=True, validat_part2=None,
            coll_ampolla={'llindar':88, 'torn':'tarda', 'setmana':'2027-W07',
                'demanda_h':120., 'oferta_h':100.})
        mapa['marge-grau-nou'].extra.update(cap_per_mida=False, validat_part2=None)
    return mapa


if __name__ == '__main__':
    import streamlit as st
    from components.vistes import franja_context
    from pagines import portada

    st.set_page_config(page_title='Com estem avui · prova inventada', page_icon='▦', layout='wide')
    st.markdown('<style>' + (ARREL / 'estil.css').read_text() + '</style>', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="marca-escola">Espais de l’Escola</div>', unsafe_allow_html=True)
        escenari = st.selectbox('Escenari inventat', ['Validat', 'Pendent de validar', 'Falten aules'])
    st.title('Com estem avui')
    st.caption('MOSTRA · Totes les dades són inventades; no són resultats del repte.')
    st.markdown(franja_context(2, None, '2027-W07'), unsafe_allow_html=True)
    st.session_state.semestre = 2
    st.session_state.setmana = None
    st.session_state.versio = ()
    st.session_state.resultats = dades_inventades(escenari)
    portada.mostra()

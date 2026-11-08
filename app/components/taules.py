"""Taules completes, amb noms i unitats llegibles i format numèric català."""
import pandas as pd
import streamlit as st
from components.format import numero

NOMS = {
    'aula':'Aula', 'dia':'Dia', 'data':'Data', 'bloc':'Franja de mitja hora (índex)',
    'ordre':'Ordre del dia', 'etiqueta':'Hora', 'valor':'Classes alhora', 'exemples':'Identificadors de sessions',
    'percent_ocupacio':'Ocupació (%)', 'classes':'Classes alhora', 'aules':'Aules disponibles',
    'aules_amb_seminaris':'Aules amb seminaris', 'torn':'Torn', 'setmana':'Setmana',
    'setmana_pitjor':'Setmana amb més ocupació', 'ocupacio_pct':'Ocupació (%)',
    'demanda_h':'Hores d’aula necessàries (h)', 'oferta_h':'Hores d’aula disponibles (h)',
    'oferta_h_amb_seminaris':'Hores amb seminaris (h)', 'llindar':'Grups amb més d’aquestes places',
    'falla':'Falten hores per aquesta mida', 'falla_amb_seminaris':'Falten hores amb seminaris',
    'demanda':'Aules necessàries', 'disponibles':'Aules disponibles', 'disponibles_amb_seminaris':'Disponibles amb seminaris',
    'hores_demanda':'Hores d’aula necessàries (h)', 'sessions_totals':'Classes del semestre',
    'sense_aula':'Classes sense aula', 'dobles':'Classes de doble titulació', 'plab':'Classes de laboratori',
    'franja':'Torn', 'cohort':'Titulació i curs', 'sessions':'Classes', 'abast':'Període',
    'sessions_directes':'Classes fora de torn, incloses les fixades', 'heretades':'Classes ja fixades',
    'hores_aula':'Hores d’aula (h)', 'hores_aula_directes':'Hores d’aula, incloses les fixades (h)',
    'alumnes':'Alumnes', 'capacitat':'Places', 'heretada':'Classe ja fixada', 'unitat':'Classe compartida (identificador)',
    'h_ini':'Hora d’inici', 'sense_dada':'Sessions sense nombre d’alumnes', 'supera':'Més alumnes que places',
    'exces':'Alumnes de més', 'problema':'Problema', 'xifra':'Casos', 'com_es_calcula':'Com es compta',
    'proposta':'Possible millora', 'minuts':'Temps d’espera (min)', 'hores':'Temps d’espera (h)',
    'linia':'Grup de teoria', 'subgrup':'Grup de pràctiques', 'aules_diferents':'Aules diferents',
    'canvis_aula':'Canvis d’aula', 'fora_passadis':'Canvis de passadís', 'passos_solapats':'Classes alhora',
    'hores_separacio':'Hores d’aula per separar classes (h)', 'docent':'Docent',
    'docents_recompte':'Docents (recompte)', 'a_cavall':'Docent amb cursos de diferents torns', 'dies_mati_tarda':'Dies amb matí i tarda', 'dies':'Dies',
    'seminaris':'Inclou seminaris', 'oferta_hores':'Hores disponibles (h)', 'demanda_hores':'Hores necessàries (h)',
    'nou_hores':'Hores del grau nou (h)', 'marge_hores':'Hores lliures abans del grau nou (h)',
    'saldo_hores':'Hores lliures després del grau nou (h)', 'variant':'Escenari',
    'marge_h':'Marge d’hores (h)', 'marge_pct':'Marge (%)', 'ordre_pitjor':'Ordre de setmana més plena',
}


# Dades que no són necessàries per interpretar cap xifra de la part 1.
# Tampoc es mostren identificadors de sessió en cap lloc de l'app.
COLUMNES_OMESES = frozenset({
    'docent', 'docents', 'id_docent', 'docent_id', 'codi', 'codi_assignatura',
    'assignatura', 'nom_assignatura', 'id_sessio', 'id_compartida', 'activitat_id',
    'unitat', 'exemples', 'grups',
})


def filtra_columnes(df):
    return df.drop(columns=[c for c in df.columns if str(c).lower() in COLUMNES_OMESES]).copy()


def resum_docents(df):
    """Una fila per docent al contracte; no s'infereix cap titulació absent."""
    if 'dies_mati_tarda' not in df:
        return pd.DataFrame({'docents_recompte':[len(df)]})
    df = df[df.dies_mati_tarda > 0]
    return df.groupby('dies_mati_tarda',dropna=False).size().reset_index(name='docents_recompte')


def taula_presentacio(t):
    if t.id == 'fora-torn' and 'per_cohort' in (t.extra or {}):
        df = pd.DataFrame(t.extra['per_cohort'])
        if 'abast' in df:
            df = df[df.abast == 'semestre']
        return filtra_columnes(df)
    return resum_docents(t.taula) if t.id == 'docents-cavall' else filtra_columnes(t.taula)


def mostra_taula(df):
    df = filtra_columnes(df)
    df = df.copy()
    for camp in ('torn', 'franja'):
        if camp in df:
            df[camp] = df[camp].replace({'mati': 'Matí', 'tarda': 'Tarda'})
    from presentacio import dates_setmana
    for camp in ('setmana', 'setmana_pitjor'):
        if camp in df:
            df[camp] = df[camp].map(dates_setmana)
    dades = df.rename(columns={c:NOMS.get(c,str(c).replace('_',' ').capitalize()) for c in df.columns}).copy()
    numeriques = list(dades.select_dtypes(include='number').columns)
    estil = dades.style.format({c:numero for c in numeriques}, na_rep='—')
    if numeriques:
        estil = estil.set_properties(subset=numeriques, **{'text-align':'right'})
    dreta = numeriques + [c for c in ('Casos',) if c in dades and c not in numeriques]
    config = {c:st.column_config.Column(alignment='right') for c in dreta}
    st.dataframe(estil, hide_index=True, width='stretch', column_config=config)


def dades_troballa(t):
    with st.expander('Detall tècnic: veure les dades', expanded=False):
        st.caption(('Desglossament de tot el semestre per titulació i curs.' if t.id == 'fora-torn' else 'Totes les files de la setmana indicada.')
                   + ' Les unitats figuren als noms de columna; pots desplaçar-te per la taula.')
        mostra_taula(taula_presentacio(t))
        if t.id == 'docents-cavall':
            st.caption('Només docents amb almenys un dia de matí i tarda; el resultat no inclou titulació i curs.')
        if t.id == 'hi-cap-mati':
            extra = t.extra or {}
            for camp,nom in [('torns','Balanç a la setmana amb més ocupació de cada torn'),
                             ('per_mida_setmanes','Comparació per mida: totes les setmanes i variants')]:
                if camp in extra:
                    st.write(nom)
                    mostra_taula(pd.DataFrame(extra[camp]))


def cohorts_classe(text):
    """Parelles titulació/curs: els dos filtres sempre han de coincidir en una parella."""
    return [tuple(c.split(':', 1)) for c in str(text or '').split('|') if ':' in c]


def filtra_classes(df, titulacio='Totes', curs='Tots'):
    df = df.copy()
    parelles = df.titulacions_curs.map(cohorts_classe)
    mask = parelles.map(lambda cs: any((titulacio == 'Totes' or t == titulacio)
        and (curs == 'Tots' or c == curs) for t, c in cs)
        if titulacio != 'Totes' or curs != 'Tots' else True)
    return df[mask].drop_duplicates('id_sessio')


def taula_classes(df):
    """Una fila per classe datada; conserva els noms i amaga els identificadors."""
    from presentacio import DIES
    df = df.copy()
    parelles = df.titulacions_curs.map(cohorts_classe)
    df['Titulació'] = parelles.map(lambda cs: ' / '.join(dict.fromkeys(t for t, _ in cs)) or 'Sense indicar')
    df['Curs'] = parelles.map(lambda cs: ' / '.join(dict.fromkeys(c for _, c in cs)) or 'Sense indicar')
    df['Dia'] = df.dia.map(DIES).fillna(df.dia)
    df['Data'] = pd.to_datetime(df.data).dt.strftime('%d/%m/%Y')
    df['Hora'] = df.h_ini.astype(str) + '–' + df.h_fi.astype(str)
    df = df.rename(columns={'assignatura': 'Assignatura', 'grup': 'Grup',
        'torn_actual': 'Torn que té', 'torn_requerit': 'Torn que li toca'})
    columnes = ['Assignatura', 'Grup', 'Dia', 'Data', 'Hora', 'Titulació', 'Curs']
    for camp in ('Torn que té', 'Torn que li toca'):
        if camp in df:
            df[camp] = df[camp].replace({'mati': 'Matí', 'tarda': 'Tarda'})
            columnes.append(camp)
    return df[columnes]


def mostra_classes(t):
    from servei import classes_detall
    from errors import mostra_error
    st.subheader('Quines classes són?')
    try:
        if 'classes_detall' in (t.extra or {}):
            df = pd.DataFrame(t.extra['classes_detall'])
        elif (t.extra or {}).get('mostra'):
            st.info('Aquesta mostra no inclou una llista de classes.')
            return
        else:
            df = classes_detall(t.id, st.session_state.semestre, st.session_state.get('versio', ()))
    except Exception:
        mostra_error()
        return
    if df.empty:
        st.write('0 classes en total al semestre.')
        return
    parelles = [p for cs in df.titulacions_curs.map(cohorts_classe) for p in cs]
    esquerra, dreta = st.columns(2)
    with esquerra:
        titulacio = st.selectbox('Titulació', ['Totes'] + sorted({t for t, _ in parelles}),
            key='classes-titulacio-' + t.id)
    with dreta:
        curs = st.selectbox('Curs', ['Tots'] + sorted({c for _, c in parelles}),
            key='classes-curs-' + t.id)
    visibles = filtra_classes(df, titulacio, curs)
    st.write(f'{numero(len(visibles))} classes amb aquests filtres · {numero(df.id_sessio.nunique())} classes en total al semestre.')
    st.caption('Cada fila és una classe en una data concreta. Les classes compartides es mostren una sola vegada, amb totes les titulacions i cursos.')
    if visibles.empty:
        st.info('Cap classe coincideix amb els filtres. Tria una altra titulació o curs.')
    else:
        st.dataframe(taula_classes(visibles), hide_index=True, width='stretch')

"""Part 2: comparació setmanal per estudiant i lliurament per aula."""
import csv
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
from components.ajuda_part2 import mostra_guia, enfoca_pas
from components.taules import mostra_taula
from errors import mostra_error
from nivell2.base import carrega_oficial, Proposta, PAQUET, GRAU_NOU
from components.graella import (grups, setmana_tipica, dilluns, celles_grup,
    celles_aula, taula_html, exporta_aula_html, resum_grup, llegenda_html)

RESULTATS = Path("/Users/bernatroca/Bernat/Hackathon/resultats/nivell2")


@st.cache_data
def carrega_dades(grau_nou=False):
    base = carrega_oficial(GRAU_NOU if grau_nou else None)
    with (PAQUET / 'activitats.csv').open(encoding='utf-8-sig', newline='') as f:
        noms = {r['codi']: r['assignatura'] for r in csv.DictReader(f)}
    with (PAQUET / 'plans.csv').open(encoding='utf-8-sig', newline='') as f:
        titulacions = {r['titulacions']: r['descripcio'] for r in csv.DictReader(f)}
    return base, noms, titulacions


@st.cache_data
def carrega_proposta(path, versio):
    return Proposta.llegeix(Path(path))


@st.cache_data
def carrega_relaxacions(path, versio):
    resultat = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        if not {'restriccio', 'sessions', 'justificacio'} <= set(lector.fieldnames or []):
            raise ValueError('Falten columnes al fitxer de relaxacions.')
        for r in lector:
            for sid in r['sessions'].split('|'):
                resultat.setdefault(sid.strip(), []).append(f"Excepció declarada ({r['restriccio']}): {r['justificacio']}")
    return resultat


def proposta_per_defecte(opcions):
    return next((p for p in ('5.2', '5.1') if p in opcions), 'Avui')


@st.cache_data
def carrega_excepcions(path, versio):
    resultat = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        if not {'id_sessio', 'data', 'minut_inici', 'motiu'} <= set(lector.fieldnames or []):
            raise ValueError('Falten columnes al fitxer d’excepcions.')
        for r in lector:
            data = date.fromisoformat(r['data'])
            minut = int(r['minut_inici'])
            if not 0 <= minut < 1440:
                raise ValueError('Hora incorrecta a les excepcions.')
            resultat.setdefault(r['id_sessio'], []).append(
                f"Excepció de calendari ({data:%d/%m/%Y}, {minut//60:02}:{minut%60:02}): {r['motiu']}")
    return resultat


NOMS_PROPOSTES = {
    '5.1': 'Assignar aules, sense canviar dies ni hores (5.1)',
    '5.2': 'Reorganitzar els torns (5.2)',
    '5.3': 'Resoldre els imprevistos (5.3)',
    '5.4': 'Incorporar el grau nou (5.4)',
}


def tria_si_cal(label, opcions, *, key, format_func=str, index=0, contenidor=st, help=None):
    """Una dada única s'explica; no es presenta com una decisió fictícia."""
    if len(opcions) == 1:
        contenidor.markdown(f'**{label}**')
        contenidor.write(format_func(opcions[0]))
        return opcions[0]
    if key in st.session_state and st.session_state[key] not in opcions:
        del st.session_state[key]
    return contenidor.selectbox(label, opcions, index=index, key=key,
        format_func=format_func, help=help)


def ancora(nom):
    st.markdown(f'<span id="{nom}"></span>', unsafe_allow_html=True)


def mostra():
    with st.container(key='p2-pagina'):
        _mostra()


def _mostra():
    st.write('**Compara l’horari actual amb una proposta de millora.** Tria els estudiants i la setmana que vols consultar.')
    st.caption('2n semestre · Pots consultar tots els cursos, amb classes al matí i a la tarda. El primer curs és només la selecció inicial.')
    mostra_guia()
    opcions = [n for n in ('5.1', '5.2', '5.3', '5.4') if (RESULTATS / n / 'proposta.csv').is_file()]
    with st.container(key='p2-seleccio-proposta'):
        ancora('p2-proposta')
        st.subheader('1. Tria què vols veure')
        comparar = bool(opcions) and st.radio('Vista',
            ['Comparar horari actual i proposta', 'Només l’horari actual'],
            horizontal=True, key='p2-vista') == 'Comparar horari actual i proposta'
        if comparar:
            preferida = proposta_per_defecte(opcions)
            triada = tria_si_cal('Millora que vols consultar', opcions, key='p2-proposta',
                index=opcions.index(preferida) if preferida in opcions else len(opcions) - 1,
                format_func=lambda n: NOMS_PROPOSTES[n])
            if triada == '5.1':
                st.info('Aquesta proposta completa i corregeix les aules. Conserva els dies i les hores de l’horari actual; encara no reorganitza els torns.')
        else:
            triada = 'Avui'
            st.info('Veus un únic horari: el que consta als fitxers originals.' if opcions
                else 'Encara no hi ha una proposta disponible. Veus l’horari que consta als fitxers originals.')
    try:
        base, noms, titulacions = carrega_dades(triada == '5.4')
        avui = Proposta.de_base(base)
        relaxacions = {}
        if triada == 'Avui':
            proposta = avui
        else:
            path = RESULTATS / triada / 'proposta.csv'
            proposta = carrega_proposta(str(path), path.stat().st_mtime_ns)
            rp = path.with_name('relaxacions.csv')
            if rp.is_file():
                relaxacions = carrega_relaxacions(str(rp), rp.stat().st_mtime_ns)
            ep = path.with_name('excepcions.csv')
            if ep.is_file():
                for sid, motius in carrega_excepcions(str(ep), ep.stat().st_mtime_ns).items():
                    relaxacions.setdefault(sid, []).extend(motius)
        tipica = setmana_tipica(base)
        setmanes = sorted({dilluns(s.data) for s in base.sessions.values()} | {date(2027, 3, 8), date(2027, 3, 15)})
        setmana = st.selectbox('Setmana que vols consultar', [None] + setmanes,
            format_func=lambda d: f'Setmana típica · {tipica:%d/%m/%Y}' if d is None else f'{d:%d/%m/%Y} – {d + timedelta(days=4):%d/%m/%Y}', key='p2-setmana') or tipica
        st.caption(f'2n semestre · Del {setmana:%d/%m/%Y} al {setmana + timedelta(days=4):%d/%m/%Y}. «Setmana típica» és una setmana representativa de les dades.')
        st.caption(('La mateixa setmana a les dues graelles. ' if comparar else '')
            + 'Les setmanes del 8 i del 15 de març inclouen els imprevistos.')
        arbre = grups(base)
        if not arbre:
            st.info('No hi ha grups d’estudiants per mostrar.')
            return
        with st.container(key='p2-seleccio-alumnat'):
            ancora('p2-alumnat')
            st.subheader('2. Tria els estudiants')
            a, b = st.columns(2)
            tit = tria_si_cal('Titulació', sorted(arbre), format_func=lambda t: titulacions.get(t, t), key='p2-titulacio', contenidor=a)
            curs = tria_si_cal('Curs', sorted(arbre[tit]), key='p2-curs', contenidor=b)
            disponibles = sorted(arbre[tit][curs])
            if len(disponibles) == 1:
                grup = disponibles[0]
                st.caption(f'Aquest curs té un únic grup d’estudiants: {grup}. No cal triar-lo.')
            else:
                grup = tria_si_cal('Grup d’estudiants', disponibles, key='p2-grup',
                    help='Alumnes que comparteixen les classes de teoria. També mostrem els seus subgrups de problemes i seminaris.')
            st.caption('Incloem la teoria del grup i els seus subgrups de problemes i seminaris. Si coincideixen dos subgrups, no vol dir que cada estudiant hagi d’anar a totes dues classes.')
        actuals = celles_grup(base, avui, setmana, tit, curs, grup, noms=noms)
        noves = celles_grup(base, proposta, setmana, tit, curs, grup, noms=noms, relaxacions=relaxacions)
        with st.container(key='p2-context-dades'):
            ancora('p2-dades')
            pendents = sum(not c.aula for c in actuals)
            if pendents:
                st.info(f'A les dades originals, {pendents} de les {len(actuals)} classes d’aquest grup no tenen l’aula indicada. '
                    'Això no vol dir que no es facin: falta aquesta informació al fitxer de partida.')
            else:
                st.caption('«Horari actual» vol dir el que consta als fitxers originals, no les classes de la data d’avui.')
            if comparar:
                assignades = sum(c.aula_assignada for c in noves)
                afectades = ({c.id_sessio for c in noves if c.canvi}
                    | ({c.id_sessio for c in actuals} - {c.id_sessio for c in noves}))
                st.subheader('Què canvia amb la proposta?')
                if not afectades:
                    st.write('**Es conserven els dies, les hores i les aules que ja constaven a les dades.**')
                else:
                    st.write(f'**{len(afectades)} classes canvien de dia, d’hora o d’una aula que ja tenien.**')
                if assignades:
                    st.write(f'La proposta afegeix una aula a **{assignades} classes** que no la tenien indicada.')
                n_aules = len({c.aula for c in noves if c.aula})
                st.write(f'El grup fa servir **{n_aules} aules diferents** aquesta setmana amb la proposta.')
                with st.expander('Detall dels canvis'):
                    st.write(resum_grup(base, proposta, actuals, noves).replace(' avui → ', ' a les dades originals → '))
                st.caption('És una comparació de canvis; no és un veredicte de validació de l’horari.')
        with st.container(key='p2-clau-colors'):
            ancora('p2-llegenda')
            st.subheader('Com es llegeixen els colors?')
            st.markdown(llegenda_html(), unsafe_allow_html=True)
        with st.container(key='p2-graelles'):
            ancora('p2-horaris')
            st.subheader('3. Consulta la setmana dels estudiants')
            st.caption('Dia sencer, de 8.30 a 21.00. Un bloc llarg és una sola classe; en mòbil pots desplaçar la graella lateralment.')
            original = taula_html(actuals, 'Horari actual · dades originals', originals=True)
            if comparar:
                st.markdown('<div class="comparacio-horaris">' + original
                    + taula_html(noves, 'Amb la proposta · ' + NOMS_PROPOSTES[triada]) + '</div>', unsafe_allow_html=True)
            else:
                st.markdown(original, unsafe_allow_html=True)
            if not actuals or (comparar and not noves):
                st.info('No hi ha classes d’aquest grup en un dels horaris de la setmana seleccionada.')
        with st.expander('Veure les dades', expanded=False):
            mostra_taula(pd.DataFrame([{'id_sessio': c.id_sessio, 'dia': c.dia,
                'h_ini': f'{c.ini//60:02}:{c.ini%60:02}', 'Hora de final': f'{c.fi//60:02}:{c.fi%60:02}',
                'Assignatura': c.assignatura, 'Tipus': c.tipus, 'Grup': c.grup,
                'aula': c.aula, 'Motiu': ' '.join(c.relaxacions)} for c in noves]))
        aules = sorted(set(base.aules) | {a.aula for a in proposta.files.values() if a.aula})
        if not aules:
            st.info('No hi ha aules disponibles.')
            return
        with st.container(key='p2-vista-aula'):
            ancora('p2-aula')
            st.subheader('4. Consulta una aula')
            st.caption('Totes les classes d’una aula, no només les del grup anterior. '
                + ('Mostrem l’horari de la proposta.' if comparar else 'Mostrem l’horari de les dades originals.'))
            aula = tria_si_cal('Aula', aules, key='p2-aula')
            dades = celles_aula(base, proposta, setmana, aula, noms=noms, relaxacions=relaxacions)
            st.markdown(taula_html(dades, 'Aula ' + aula, originals=not comparar), unsafe_allow_html=True)
            if not dades:
                st.info('Aquesta aula no té classes assignades aquesta setmana.')
            st.download_button('Descarrega l’horari d’aquesta aula',
                exporta_aula_html(base, proposta, setmana, aula, noms=noms, relaxacions=relaxacions),
                file_name=f'horari-{aula.replace("/", "-")}-{setmana}.html', mime='text/html')
        enfoca_pas()
    except Exception:
        mostra_error()

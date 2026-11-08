"""Part 2: comparació setmanal per estudiant i lliurament per aula."""
import csv
import re
from datetime import date, timedelta
from pathlib import Path
from html import escape

import streamlit as st
import pandas as pd
from components.ajuda_part2 import mostra_guia, enfoca_pas, CSS_GUIA
from components.taules import mostra_taula
from components.vistes import estat
from errors import mostra_error
from nivell2.base import carrega_oficial, Proposta, PAQUET, GRAU_NOU
from nivell2 import junta
from nivell2.s52 import MOTIU_FIXADES
from components.graella import (grups, setmana_tipica, dilluns, celles_grup,
    celles_aula, taula_html, exporta_aula_html, resum_grup, canvis_grup, ESTATS, CSS as CSS_GRAELLA, CSS_FILTRES, recomptes_estat, nom_grup)

from nivell2.base import RESULTATS_PRINCIPAL; RESULTATS = RESULTATS_PRINCIPAL


@st.cache_data
def carrega_dades(grau_nou=False):
    base = carrega_oficial(GRAU_NOU if grau_nou else None)
    with (PAQUET / 'activitats.csv').open(encoding='utf-8-sig', newline='') as f:
        noms = {r['codi']: r['assignatura'] for r in csv.DictReader(f)}
    if grau_nou:
        with (GRAU_NOU / 'sessions_extra.csv').open(encoding='utf-8-sig', newline='') as f:
            noms.update({r['codi']: r['assignatura'] for r in csv.DictReader(f)})
    titulacions = {**junta.NOMS, 'GNOU': 'Grau nou (40 places)'}
    return base, noms, titulacions


@st.cache_data
def carrega_proposta(path, versio):
    return Proposta.llegeix(Path(path))


def motiu_visible(text):
    """Explica les regles a la persona que prepara l'horari."""
    equivalencies = {
        'R1-TORN': 'Es manté fora del seu torn perquè no es pot moure',
        'R2-CALENDARI': 'dia no lectiu',
        'R4-ALUMNAT': 'coincideix amb una altra classe del grup',
        'R4-AULA': 'l’aula està ocupada',
        'R4-DOCENT': 'el professor té una altra classe',
    }
    text = re.sub(r'Restauració al patró rebutjada:\s*(?:restriccions oficials:\s*)?', '', text)
    text = text.replace('supera el límit de qualitat de la variant de referència',
                        'empitjorava massa la resta de l’horari')
    for codi, explicacio in equivalencies.items():
        text = text.replace(codi, explicacio)
    text = junta.motiu_planer(text)
    text = re.sub(r'R\d+(?:-[A-ZÀ-Ü]+)?', 'regla de l’horari', text)
    text = re.sub(r'(?:\.\./[\w./-]+/)?[\w-]+\.md', 'el diagnòstic', text)
    return text.replace('variant de referència', 'horari de comparació').strip()


@st.cache_data
def carrega_relaxacions(path, versio):
    resultat = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        if not {'restriccio', 'sessions', 'justificacio'} <= set(lector.fieldnames or []):
            raise ValueError('Falten columnes al fitxer de relaxacions.')
        for r in lector:
            for sid in r['sessions'].split('|'):
                sid = sid.strip()
                if not sid:
                    continue
                if r['justificacio'] == MOTIU_FIXADES:
                    motiu = 'Classe fixada de 1r/2n: no es mou (regla 1)'
                elif sid == 'S04526' and junta.es_motiu_avaluacio(r['justificacio']):
                    motiu = 'Excepció demostrada: ' + junta.motiu_planer(junta.MOTIU_S04526).replace('S04526', 'Aquesta classe')
                else:
                    motiu = motiu_visible(r['justificacio'])
                    if r['restriccio'] == 'R1-TORN':
                        motiu = 'Es manté fora del seu torn perquè no es pot moure. ' + motiu
                resultat.setdefault(sid, []).append(motiu)
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
                f"Fora de l’hora habitual ({data:%d/%m/%Y}, {minut//60:02}:{minut%60:02}): "
                f"no s’ha pogut tornar a la seva hora habitual perquè {motiu_visible(r['motiu'])}")
    return resultat


NOMS_PROPOSTES = {
    '5.1': 'Aules assignades (5.1)',
    '5.2': 'Torns nous (5.2)',
    '5.3': 'Resoldre els imprevistos (5.3)',
    '5.4': 'Incorporar el grau nou (5.4)',
}


def tria_si_cal(label, opcions, *, key, format_func=str, index=0, contenidor=st, help=None):
    """Manté la mateixa etiqueta i alçada quan només hi ha una opció."""
    if key in st.session_state and st.session_state[key] not in opcions:
        st.session_state[key] = opcions[index]
    return contenidor.selectbox(label, opcions, index=index, key=key,
        format_func=format_func, help=help, disabled=len(opcions) == 1)


def mostra():
    with st.container(key='p2-pagina'):
        _mostra()


CSS_PAGINA = """
.st-key-p2-pagina{--p2-taronja:#e8820c;--p2-taronja-fons:#fff1e0;--p2-taronja-text:#9a5200;gap:12px;}
.st-key-p2-pagina .p2-intro{color:var(--tinta-2);margin:0 0 2px;}
.st-key-p2-pagina .st-key-p2-controls{background:var(--targeta,#fff);border:1px solid var(--linia);border-radius:14px;padding:12px 16px;gap:10px;}
.st-key-p2-pagina .st-key-p2-controls [data-testid="stHorizontalBlock"]{gap:14px;align-items:end;}
.st-key-p2-pagina .st-key-p2-controls [data-testid="stColumn"]{min-width:0!important;}
.st-key-p2-pagina .st-key-p2-controls [data-testid="stVerticalBlock"]{gap:4px;}
.st-key-p2-pagina .st-key-p2-controls p{font-size:14px;margin:0;}
.st-key-p2-pagina .p2-resum{background:var(--targeta,#fff);border:1px solid var(--linia);border-left:6px solid var(--verd);border-radius:14px;padding:12px 18px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,360px);gap:20px;align-items:center;}
.st-key-p2-pagina .p2-resum.amb-canvis{border-left-color:var(--p2-taronja);}
.st-key-p2-pagina .p2-resum.actual{border-left-color:var(--blau);}
.st-key-p2-pagina .p2-resum.actual .estat{background:var(--blau-fons,#eef5fd);color:var(--blau);}
.st-key-p2-pagina .p2-resum p{font-size:15px;margin:4px 0 0;}
.st-key-p2-pagina .p2-resum .estat{margin:0;}
.st-key-p2-pagina .p2-resum .estat.ambre{background:var(--p2-taronja-fons);color:var(--p2-taronja-text);}
.st-key-p2-pagina .p2-xifres{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;min-width:0;width:100%;}
.st-key-p2-pagina .p2-xifres div{text-align:center;min-width:0;}
.st-key-p2-pagina .p2-xifres b{display:block;font-size:28px;line-height:1.2;font-variant-numeric:tabular-nums;}
.st-key-p2-pagina .p2-xifres span{display:block;font-size:12px;color:var(--tinta-2);}
.st-key-p2-pagina .st-key-p2-graelles{margin-top:24px;min-width:0;max-width:100%;}
.st-key-p2-pagina h3{font-size:20px!important;padding:4px 0;}
.st-key-p2-pagina .st-key-p2-vista-aula button{color:#256abf;}
.st-key-p2-pagina .st-key-p2-guia{position:fixed;left:18px;top:80px;width:350px;max-height:calc(100vh - 24px);overflow:auto;z-index:1000001;background:var(--targeta,#fff);border:2px solid var(--blau);border-radius:14px;padding:16px;box-shadow:0 6px 28px #0003;gap:8px;}
.st-key-p2-pagina .st-key-p2-guia p{font-size:14px;}
.st-key-p2-pagina .st-key-p2-guia button{color:#256abf;}
.st-key-p2-pagina .st-key-p2-guia [data-testid="stHorizontalBlock"]{flex-wrap:nowrap;gap:6px;}
.st-key-p2-pagina .st-key-p2-guia [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important;width:auto!important;}
.st-key-p2-pagina .p2-pas-actiu{position:relative;z-index:1000000;background:var(--targeta,#fff);outline:3px solid var(--blau);outline-offset:5px;border-radius:10px;box-shadow:0 0 0 100vmax #10182070;scroll-margin-top:80px;}
.st-key-p2-pagina .p2-horari.p2-pas-actiu{max-height:48vh;overflow-y:auto;}
.st-key-p2-pagina .st-key-p2-vista-aula.p2-pas-actiu{max-height:48vh;overflow:auto;}
@media(prefers-reduced-motion:reduce){.st-key-p2-pagina *{scroll-behavior:auto!important;transition:none!important;animation:none!important;}}
@container contingut (max-width:680px){
 .st-key-p2-pagina .p2-resum{grid-template-columns:minmax(0,1fr);gap:12px;}
 .st-key-p2-pagina .st-key-p2-controls [data-testid="stHorizontalBlock"]{flex-wrap:wrap;}
 .st-key-p2-pagina .st-key-p2-controls [data-testid="stColumn"]{flex:1 1 140px!important;width:auto!important;}
}
""" + CSS_GUIA


def estil_pagina():
    st.markdown('<style>' + CSS_PAGINA + CSS_FILTRES
        + CSS_GRAELLA + '</style>', unsafe_allow_html=True)


def selecciona_filtre(clau):
    st.session_state['p2-filtre'] = clau


def mostra_filtres(celles):
    comptes = recomptes_estat(celles)
    actiu = st.session_state.get('p2-filtre', 'totes')
    if actiu not in ESTATS or (actiu != 'totes' and comptes[actiu] == 0):
        st.session_state['p2-filtre'] = actiu = 'totes'
    with st.container(key='p2-filtres'):
        for columna, (clau, (nom, *_)) in zip(st.columns(len(ESTATS)), ESTATS.items()):
            with columna, st.container(key='p2-filtre-' + clau):
                n = sum(comptes.values()) if clau == 'totes' else comptes[clau]
                st.button(f'{nom} ({n})', key='p2-boto-' + clau,
                    type='primary' if actiu == clau else 'secondary',
                    on_click=selecciona_filtre, args=(clau,))
    return actiu


def resum_html(base, proposta, actuals, noves, comparar, *, referencia=None, nom_referencia='avui'):
    canvis = canvis_grup(base, proposta, actuals, noves, referencia=referencia)
    franja, aula, assignades = (canvis[k] for k in ('franja', 'aula', 'assignades'))
    n_aules = len({c.aula for c in noves if c.aula})
    amb_canvis = franja or aula
    etiqueta = ('Canvis en aquest grup' if amb_canvis else 'Es conserva el dia i l’hora') if comparar else 'Horari d’avui · dades originals'
    parts = [f'{n} {"classe " + singular if n == 1 else "classes " + plural}'
             for n, singular, plural in ((franja, 'canvia de dia o hora', 'canvien de dia o hora'),
                 (aula, 'canvia d’aula', 'canvien d’aula'), (assignades, 'rep aula', 'reben aula')) if n]
    frase = ('; '.join(parts) + '.' if parts else 'Cap classe d’aquest grup canvia.') if comparar else 'Consulta les classes del grup a la setmana seleccionada.'
    if comparar and noves and all(c.horari_nou for c in noves):
        etiqueta, frase = 'Grau nou: horari nou', 'Aquest grup té un horari nou, sense horari anterior per comparar.'
    elif comparar and nom_referencia != 'avui':
        frase += f' Comparació amb {nom_referencia}.'
    classe = ('amb-canvis' if amb_canvis else '') if comparar else 'actual'
    indicadors = ((franja, 'canvis d’hora'), (aula, 'canvis d’aula'), (n_aules, 'aules a la setmana')) if comparar else (
        (len(actuals), 'classes'), (f'{sum(c.fi - c.ini for c in actuals) / 60:g}', 'hores de classe'),
        (sum(not c.aula and not c.ubicacio_compartida for c in actuals), 'sense aula a les dades'))
    if comparar and noves and all(c.horari_nou for c in noves):
        indicadors = ((len(noves), 'classes noves'), (f'{sum(c.fi - c.ini for c in noves) / 60:g}', 'hores de classe'), (n_aules, 'aules a la setmana'))
    xifres = ''.join(f'<div><b>{n}</b><span>{text}</span></div>' for n, text in indicadors)
    return (f'<section class="p2-resum {classe}"><div>'
        + estat({'estat': 'ambre' if amb_canvis else 'verd', 'etiqueta': etiqueta})
        + f'<p>{escape(frase)}</p></div><div class="p2-xifres">{xifres}</div></section>')


def _mostra():
    estil_pagina()
    st.markdown('<p class="p2-intro">Consulta la setmana del grup i descobreix què canvia amb la proposta.</p>', unsafe_allow_html=True)
    mostra_guia()
    opcions = [n for n in ('5.1', '5.2', '5.3', '5.4') if (RESULTATS / n / 'proposta.csv').is_file()]
    try:
        with st.container(key='p2-controls'):
            a, b, c = st.columns([2, 2, 2])
            with a, st.container(key='p2-seleccio-proposta'):
                vista = st.segmented_control('Què vols veure', ['Proposta i avui', 'Només avui'],
                    default='Proposta i avui' if opcions else 'Només avui', key='p2-vista',
                    selection_mode='single', required=True, disabled=not opcions)
                comparar = bool(opcions) and vista == 'Proposta i avui'
            with b:
                preferida = proposta_per_defecte(opcions)
                triada = st.selectbox('Proposta', opcions or ['Avui'], key='p2-proposta',
                    index=opcions.index(preferida) if preferida in opcions else 0,
                    format_func=lambda n: NOMS_PROPOSTES.get(n, 'Avui'), disabled=not comparar)
            if not comparar:
                triada = 'Avui'
            base, noms, titulacions = carrega_dades(triada == '5.4')
            avui = Proposta.de_base(base)
            nom_referencia = 'avui'
            referencia_path = RESULTATS / '5.2' / 'proposta.csv'
            if triada == '5.3' and referencia_path.is_file():
                avui = carrega_proposta(str(referencia_path), referencia_path.stat().st_mtime_ns)
                nom_referencia = NOMS_PROPOSTES['5.2']
            elif triada == '5.3':
                st.info('No hi ha Torns nous (5.2) per comparar. Es compara amb l’horari original.')
            relaxacions = {}
            proposta = avui
            if comparar:
                path = RESULTATS / triada / 'proposta.csv'
                proposta = carrega_proposta(str(path), path.stat().st_mtime_ns)
                rp = path.with_name('relaxacions.csv')
                if rp.is_file():
                    relaxacions = carrega_relaxacions(str(rp), rp.stat().st_mtime_ns)
                ep = path.with_name('excepcions.csv')
                if ep.is_file():
                    for sid, motius in carrega_excepcions(str(ep), ep.stat().st_mtime_ns).items():
                        relaxacions.setdefault(sid, []).extend(motius)
                if triada == '5.3':
                    relaxacions.setdefault('S11527', []).append('Recuperació de la classe cancel·lada')
            tipica = setmana_tipica(base)
            setmanes = sorted({dilluns(s.data) for s in base.sessions.values()} | {date(2027, 3, 8), date(2027, 3, 15)})
            setmana = c.selectbox('Setmana', [None] + setmanes,
                format_func=lambda d: (f'Típica · {tipica:%d/%m}' if d is None else f'{d:%d/%m} – {d + timedelta(days=4):%d/%m}')
                    + (' · imprevistos' if triada == '5.3' and (d or tipica) in (date(2027, 3, 8), date(2027, 3, 15)) else ''), key='p2-setmana') or tipica
            arbre = grups(base)
            if not arbre:
                st.info('No hi ha grups d’estudiants per mostrar.')
                return
            with st.container(key='p2-seleccio-alumnat'):
                a, b, c = st.columns([3, 1, 2])
                tit = tria_si_cal('Estudis', sorted(arbre, key=lambda t: titulacions.get(t, 'Estudis sense nom')),
                    format_func=lambda t: titulacions.get(t, 'Estudis sense nom'), key='p2-titulacio', contenidor=a)
                curs = tria_si_cal('Curs', sorted(arbre[tit], key=lambda c: (c == '?', c)),
                    format_func=lambda c: 'Sense curs a les dades' if c == '?' else c, key='p2-curs', contenidor=b)
                grups_disponibles = sorted(arbre[tit][curs])
                context_grup = (tit, curs)
                if st.session_state.get('p2-context-grup') != context_grup:
                    st.session_state['p2-grup'] = grups_disponibles[0]
                    st.session_state['p2-context-grup'] = context_grup
                    st.session_state['p2-filtre'] = 'totes'
                grup = tria_si_cal('Grup', grups_disponibles, key='p2-grup',
                    format_func=lambda g: f'Grup {g}', contenidor=c)
        context_filtre = (tit, curs, grup, triada, setmana, comparar)
        if st.session_state.get('p2-context-filtre') != context_filtre:
            st.session_state['p2-filtre'] = 'totes'
            st.session_state['p2-context-filtre'] = context_filtre
        actuals = celles_grup(base, avui, setmana, tit, curs, grup, noms=noms, referencia=avui)
        noves = celles_grup(base, proposta, setmana, tit, curs, grup, noms=noms, relaxacions=relaxacions, referencia=avui)
        with st.container(key='p2-context-dades'):
            st.markdown(resum_html(base, proposta, actuals, noves, comparar, referencia=avui, nom_referencia=nom_referencia), unsafe_allow_html=True)
        with st.container(key='p2-graelles'):
            st.subheader('La setmana del grup')
            with st.container(key='p2-clau-colors'):
                filtre = mostra_filtres(noves)
            titol = f'{"Proposta" if comparar else "Avui"} · Grup {grup} · {setmana:%d/%m} – {setmana + timedelta(days=4):%d/%m}'
            if comparar and nom_referencia != 'avui':
                titol += f' · respecte de {nom_referencia}'
            st.markdown(taula_html(noves, titol, originals=not comparar, filtre=filtre, estils=False), unsafe_allow_html=True)
        with st.expander('Més informació', expanded=False):
            st.write('«Avui» és l’horari dels fitxers originals, no la data d’avui. La graella inclou la teoria i els subgrups de problemes i seminaris; els subgrups simultanis no impliquen que cada estudiant assisteixi a tots.')
            st.write('Setmana típica: una setmana representativa del segon semestre. El resum descriu canvis, no és un veredicte de validació.')
            if triada == '5.3':
                st.write('Les setmanes del 8 i del 15 de març inclouen els imprevistos.')
            if not (noves and all(c.horari_nou for c in noves)):
                st.write(resum_grup(base, proposta, actuals, noves, referencia=avui, nom_referencia=nom_referencia))
            if len(arbre[tit][curs]) == 1:
                st.caption(f'Aquest curs té un únic grup d’estudiants: {grup}.')
        with st.expander('Veure les dades', expanded=False):
            mostra_taula(pd.DataFrame([{'id_sessio': c.id_sessio, 'dia': c.dia,
                'h_ini': f'{c.ini//60:02}:{c.ini%60:02}', 'Hora de final': f'{c.fi//60:02}:{c.fi%60:02}',
                'Assignatura': c.assignatura, 'Tipus': c.tipus, 'Grup': nom_grup(c.grup, c.tipus),
                'aula': c.aula, 'Motiu': ' '.join(c.relaxacions)} for c in noves]))
        aules = sorted(set(base.aules) | {a.aula for a in proposta.files.values() if a.aula})
        if aules:
            with st.container(key='p2-vista-aula'):
                st.subheader('Consulta una aula')
                aula = tria_si_cal('Aula', aules, key='p2-aula', format_func=lambda a:
                    f'{a} · {base.aules[a].capacitat} places' if a in base.aules else a)
                dades = celles_aula(base, proposta, setmana, aula, noms=noms, relaxacions=relaxacions, referencia=avui)
                st.download_button('Descarrega l’horari d’aquesta aula',
                    exporta_aula_html(base, proposta, setmana, aula, noms=noms, relaxacions=relaxacions,
                        referencia=avui, nom_proposta=NOMS_PROPOSTES.get(triada, 'Horari d’avui')),
                    file_name=f'horari-{aula.replace("/", "-")}-{triada}-{setmana}.html', mime='text/html')
                st.markdown(taula_html(dades, 'Aula ' + aula, originals=not comparar, estils=False), unsafe_allow_html=True)
        enfoca_pas()
    except Exception:
        mostra_error()

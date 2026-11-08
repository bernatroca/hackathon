"""Part 2: comparació setmanal per estudiant i lliurament per aula."""
import csv
from collections import Counter
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
from nivell2.base import carrega_oficial, Proposta, PAQUET, GRAU_NOU, CONTINGENCIES
from nivell2 import junta
from nivell2.s52 import MOTIU_FIXADES
from components.graella import (grups, setmana_tipica, dilluns, celles_grup,
    celles, celles_aula, taula_html, exporta_aula_html, resum_grup, canvis_grup, ESTATS, CSS as CSS_GRAELLA, CSS_FILTRES, recomptes_estat, nom_grup, frase_classes, aules_visibles, partida, DIES, NOMS_DIES)

from nivell2.base import RESULTATS_PRINCIPAL; RESULTATS = RESULTATS_PRINCIPAL


@st.cache_data
def carrega_dades(grau_nou=False):
    base = carrega_oficial(GRAU_NOU if grau_nou else None)
    with (PAQUET / 'activitats.csv').open(encoding='utf-8-sig', newline='') as f:
        noms = {r['codi']: r['assignatura'] for r in csv.DictReader(f)}
    if grau_nou:
        with (GRAU_NOU / 'sessions_extra.csv').open(encoding='utf-8-sig', newline='') as f:
            noms.update({r['codi']: r['assignatura'] for r in csv.DictReader(f)})
    titulacions = {**junta.NOMS, 'MRICSE': 'Màster RICSE', 'GNOU': 'Grau nou (40 places)'}
    return base, noms, titulacions


@st.cache_data
def carrega_proposta(path, versio):
    return Proposta.llegeix(Path(path))


def motiu_visible(text):
    """Explica les regles a la persona que prepara l'horari."""
    equivalencies = {
        'R1-TORN': 'Es manté fora del seu torn perquè no es pot moure',
        'R2-CALENDARI': 'hi ha una aturada o un dia sense classes al calendari',
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
            if r['id_sessio'] == 'S04526':
                continue  # Ja té el motiu d’excepció demostrada.
            data = date.fromisoformat(r['data'])
            minut = int(r['minut_inici'])
            if not 0 <= minut < 1440:
                raise ValueError('Hora incorrecta a les excepcions.')
            resultat.setdefault(r['id_sessio'], []).append(
                f"Fora de l’hora habitual ({data:%d/%m/%Y}, {minut//60:02}:{minut%60:02}): "
                f"a la seva hora habitual no hi cabia: {motiu_visible(r['motiu'])}")
    return resultat


# Noms visibles de les propostes.
NOMS_PROPOSTES = {
    'Avui': 'Avui',
    '5.1': 'Aules assignades (5.1)',
    '5.2': 'Torns nous (5.2)',
    '5.3': 'Resoldre els imprevistos (5.3)',
    '5.4': 'Incorporar el grau nou (5.4)',
}


def opcions_setmana(base, tipica):
    comptes = Counter(dilluns(s.data) for s in base.sessions.values())
    completes = {d for d, n in comptes.items() if n >= 200}
    # Les bases inventades petites continuen sent navegables a les proves.
    disponibles = completes or set(comptes)
    return sorted((disponibles | {date(2027, 3, 8), date(2027, 3, 15)}) - {tipica})


def motius_imprevistos(base, contingencies, referencia, proposta, noms):
    """Causes de cada canvi i de les classes que deixen l'aula a una afectada."""
    motius, moments = {}, {}
    for sid, s in base.sessions.items():
        abans = partida(s, referencia)
        despres = partida(s, proposta)
        moments[sid] = (abans, despres)
        if abans == despres:
            continue
        data, ini, aula = abans
        if sid in contingencies.cancellades:
            motius[sid] = 'Recuperació de la classe cancel·lada'
            continue
        alumnes = contingencies.sessions[sid].alumnes
        causes = []
        if alumnes > s.alumnes:
            causes.append(f'El grup passa de {s.alumnes} a {alumnes} alumnes durant tot el semestre i necessita una aula amb més places que {aula}.')
        for t in contingencies.tancaments:
            if aula == t.aula and t.data_ini <= data <= t.data_fi and ini < t.fi and ini + s.durada > t.ini:
                periode = f'el {t.data_ini:%d/%m}' if t.data_ini == t.data_fi else f'del {t.data_ini:%d/%m} al {t.data_fi:%d/%m}'
                causes.append(f'L’aula {aula} està tancada {periode}.')
        if causes:
            motius[sid] = ' '.join(causes)
    directes = dict(motius)
    for sid, (abans, despres) in moments.items():
        if sid in motius or abans == despres:
            continue
        s = base.sessions[sid]
        data, ini, aula = abans
        for altra in directes:
            d, h, a = moments[altra][1]
            if aula and a == aula and d == data and h < ini + s.durada and ini < h + base.sessions[altra].durada:
                afectada = base.sessions[altra]
                motius[sid] = (f'Es mou per deixar l’aula al grup {afectada.num_grup} de '
                               f'{noms.get(afectada.codi, "la classe afectada")}.')
                break
        else:
            motius[sid] = 'Es mou per fer lloc a les classes afectades pels imprevistos.'
    return motius


@st.cache_data(show_spinner=False)
def carrega_motius_imprevistos(referencia, proposta, noms):
    from nivell2.imprevistos import calcula
    return calcula(carrega_oficial(), carrega_oficial(CONTINGENCIES),
                   referencia, proposta, [], noms=noms)['motius_per_sessio']


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
.st-key-p2-pagina .p2-xifres{display:grid;grid-template-columns:repeat(auto-fit,minmax(70px,1fr));gap:12px;min-width:0;width:100%;}
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


def mostra_filtres(celles, comparar=True):
    comptes = recomptes_estat(celles)
    actiu = st.session_state.get('p2-filtre', 'totes')
    if not comparar or actiu not in ESTATS or (actiu != 'totes' and comptes[actiu] == 0):
        st.session_state['p2-filtre'] = actiu = 'totes'
    with st.container(key='p2-filtres'):
        estats = ESTATS if comparar else {'totes': ESTATS['totes']}
        for columna, (clau, (nom, *_)) in zip(st.columns(len(estats)), estats.items()):
            with columna, st.container(key='p2-filtre-' + clau):
                n = sum(comptes.values()) if clau == 'totes' else comptes[clau]
                st.button(f'{nom} ({n})', key='p2-boto-' + clau,
                    type='primary' if actiu == clau else 'secondary',
                    on_click=selecciona_filtre, args=(clau,), disabled=n == 0 and clau != 'totes')
    return actiu


def resum_html(base, proposta, actuals, noves, comparar, *, referencia=None, nom_referencia='avui'):
    canvis = canvis_grup(base, proposta, actuals, noves, referencia=referencia)
    franja, aula, assignades = (canvis[k] for k in ('franja', 'aula', 'assignades'))
    n_aules = len(aules_visibles(noves))
    amb_canvis = franja or aula
    etiqueta = ('Canvis en aquest grup' if amb_canvis else 'Es conserva el dia i l’hora') if comparar else 'Horari d’avui · dades originals'
    parts = [frase_classes(n, singular, plural)
             for n, singular, plural in ((franja, 'canvia de dia o hora', 'canvien de dia o hora'),
                 (aula, 'canvia d’aula', 'canvien d’aula'), (assignades, 'rep aula', 'reben aula')) if n]
    frase = ('; '.join(parts) + '.' if parts else 'Cap classe d’aquest grup canvia.') if comparar else 'Consulta les classes del grup a la setmana seleccionada.'
    if comparar and noves and all(c.horari_nou for c in noves):
        etiqueta, frase = 'Grau nou: horari nou', 'Aquest grup té un horari nou, sense horari anterior per comparar.'
    elif comparar and nom_referencia != 'avui':
        frase += f' Comparació amb {nom_referencia}.'
    classe = ('amb-canvis' if amb_canvis else '') if comparar else 'actual'
    if not noves:
        etiqueta = 'Aquest grup no té classes aquesta setmana'
        frase = 'Tria una altra setmana per veure les classes del grup.'
        classe = 'actual'
    indicadors = ((franja, 'canvis d’hora'), (aula, 'canvis d’aula'),
        (n_aules, 'aules a la setmana')) if comparar else (
        (len(actuals), 'classes'), (f'{sum(c.fi - c.ini for c in actuals) / 60:g}', 'hores de classe'),
        (sum(not c.aula and not c.ubicacio_compartida for c in actuals), 'sense aula a les dades'))
    if comparar and assignades:
        indicadors = indicadors[:2] + ((assignades, 'classe rep aula' if assignades == 1 else 'classes reben aula'),) + indicadors[2:]
    if comparar and noves and all(c.horari_nou for c in noves):
        indicadors = ((len(noves), 'classes noves'), (f'{sum(c.fi - c.ini for c in noves) / 60:g}', 'hores de classe'), (n_aules, 'aules a la setmana'))
    xifres = ''.join(f'<div><b>{n}</b><span>{text}</span></div>' for n, text in indicadors)
    return (f'<section class="p2-resum {classe}"><div>'
        + (f'<span class="estat">{escape(etiqueta)}</span>' if not noves else
           estat({'estat': 'ambre' if amb_canvis else 'verd', 'etiqueta': etiqueta}))
        + f'<p>{escape(frase)}</p></div><div class="p2-xifres">{xifres}</div></section>')


def tria_exemple(base, proposta):
    """Cas estable: canvi d'hora i aula, prioritzant setmanes llegibles."""
    setmana = setmana_tipica(base)
    classes = celles(base, proposta, setmana)
    candidats = []
    for tit, cursos in grups(base).items():
        for curs, grups_curs in cursos.items():
            for grup, linia in grups_curs.items():
                visibles = [c for c in classes
                    if f'{tit}:{curs}' in base.sessions[c.id_sessio].cohorts
                    and base.sessions[c.id_sessio].linia == linia
                    and base.sessions[c.id_sessio].tipus in ('TE', 'PAUL', 'SEM')]
                canvien = [c for c in visibles if c.canvi_franja and c.canvi_aula
                    and c.ini != base.sessions[c.id_sessio].ini]
                if not canvien:
                    continue
                coincidencies = sum(a.dia == b.dia and a.ini < b.fi and b.ini < a.fi
                    for i, a in enumerate(visibles) for b in visibles[i + 1:])
                candidats.append((coincidencies, len(visibles), tit, curs, grup,
                    min(c.id_sessio for c in canvien)))
    return min(candidats)[2:] if candidats else None


def aplica_exemple(cas):
    tit, curs, grup, _ = cas
    st.session_state.update({'p2-proposta': '5.2', 'p2-vista': 'Proposta i avui',
        'p2-setmana': None, 'p2-titulacio': tit, 'p2-curs': curs, 'p2-grup': grup,
        'p2-context-grup': (tit, curs), 'p2-filtre': 'totes'})


def _mostra():
    estil_pagina()
    st.markdown('<p class="p2-intro">Tria un grup i mira com queda la seva setmana. Els colors diuen què canvia respecte d’avui.</p>', unsafe_allow_html=True)
    mostra_guia()
    opcions = [n for n in ('5.1', '5.2', '5.3', '5.4') if (RESULTATS / n / 'proposta.csv').is_file()]
    try:
        if '5.2' in opcions:
            path_exemple = RESULTATS / '5.2' / 'proposta.csv'
            versio_exemple = path_exemple.stat().st_mtime_ns
            if st.session_state.get('p2-exemple-versio') != (str(path_exemple), versio_exemple):
                base_exemple, _, _ = carrega_dades()
                st.session_state['p2-exemple'] = tria_exemple(base_exemple,
                    carrega_proposta(str(path_exemple), versio_exemple))
                st.session_state['p2-exemple-versio'] = (str(path_exemple), versio_exemple)
            cas = st.session_state.get('p2-exemple')
            if cas:
                if 'p2-proposta' not in st.session_state:
                    aplica_exemple(cas)
                st.button('Mira l’exemple', on_click=aplica_exemple, args=(cas,))
        with st.container(key='p2-controls'):
            opcions_extra = st.expander('Més opcions',
                expanded=st.session_state.get('p2-guia-pas') in (3, 5))
            with opcions_extra, st.container(key='p2-seleccio-proposta'):
                vista = st.segmented_control('Què vols veure', ['Proposta i avui', 'Només avui'],
                    default='Proposta i avui' if opcions else 'Només avui', key='p2-vista',
                    selection_mode='single', required=True, disabled=not opcions)
                comparar = bool(opcions) and vista == 'Proposta i avui'
            with st.container():
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
            if triada in ('5.3', '5.4') and referencia_path.is_file():
                referencia_52 = carrega_proposta(str(referencia_path), referencia_path.stat().st_mtime_ns)
                avui = Proposta({**avui.files, **referencia_52.files})
                nom_referencia = NOMS_PROPOSTES['5.2']
            elif triada in ('5.3', '5.4'):
                st.info('No hi ha Torns nous (5.2) per comparar. Es compara amb l’horari original.')
            relaxacions = {}
            proposta = avui
            if comparar:
                path = RESULTATS / triada / 'proposta.csv'
                proposta = carrega_proposta(str(path), path.stat().st_mtime_ns)
                rp = path.with_name('relaxacions.csv')
                if rp.is_file():
                    relaxacions = carrega_relaxacions(str(rp), rp.stat().st_mtime_ns)
                ep = (RESULTATS / '5.2' / 'excepcions.csv') if triada == '5.4' else path.with_name('excepcions.csv')
                if ep.is_file():
                    for sid, motius in carrega_excepcions(str(ep), ep.stat().st_mtime_ns).items():
                        relaxacions.setdefault(sid, []).extend(motius)
                if triada == '5.3':
                    for sid, motiu in carrega_motius_imprevistos(avui, proposta, noms).items():
                        relaxacions.setdefault(sid, []).append(motiu)
                    relaxacions.setdefault('S11527', []).append('Recuperació de la classe cancel·lada')
            tipica = setmana_tipica(base)
            setmanes = opcions_setmana(base, tipica)
            if st.session_state.get('p2-setmana') not in [None] + setmanes:
                st.session_state['p2-setmana'] = None
            setmana = opcions_extra.selectbox('Setmana', [None] + setmanes,
                format_func=lambda d: (f'Típica · {tipica:%d/%m}' if d is None else f'{d:%d/%m} – {d + timedelta(days=4):%d/%m}')
                    + (' · poques classes' if d and sum(dilluns(s.data) == d for s in base.sessions.values()) < 200 else '')
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
                    format_func=lambda c: 'Sense curs a les dades' if c == '?' else 'Màster' if c == 'M' else c, key='p2-curs', contenidor=b)
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
        cas = st.session_state.get('p2-exemple')
        if cas and triada == '5.2' and (tit, curs, grup) == cas[:3] and setmana == tipica:
            classe_exemple = next((c for c in noves if c.id_sessio == cas[3]), None)
            if classe_exemple:
                st.caption(f'Exemple · {classe_exemple.assignatura} · '
                    f'{classe_exemple.abans} → {NOMS_DIES[DIES.index(classe_exemple.dia)].lower()} '
                    f'{classe_exemple.ini//60:02}:{classe_exemple.ini%60:02} · {classe_exemple.aula}. '
                    'Obre aquesta classe per veure’n el detall.')
        with st.container(key='p2-context-dades'):
            st.markdown(resum_html(base, proposta, actuals, noves, comparar, referencia=avui, nom_referencia=nom_referencia), unsafe_allow_html=True)
        with st.container(key='p2-graelles'):
            st.subheader('La setmana del grup')
            with opcions_extra, st.container(key='p2-clau-colors'):
                filtre = mostra_filtres(noves, comparar)
            titol = f'{"Proposta" if comparar else "Avui"} · Grup {grup} · {setmana:%d/%m} – {setmana + timedelta(days=4):%d/%m}'
            if comparar and nom_referencia != 'avui':
                titol += f' · respecte de {nom_referencia}'
            st.markdown(taula_html(noves, titol, originals=not comparar, filtre=filtre, estils=False), unsafe_allow_html=True)
        with st.expander('Més informació', expanded=False):
            st.write('«Avui» és l’horari dels fitxers originals, no la data d’avui. La graella inclou la teoria i els subgrups de problemes i seminaris; els subgrups simultanis no impliquen que cada estudiant assisteixi a tots.')
            st.write('Setmana típica: una setmana representativa del segon semestre. El resum descriu canvis, no és un veredicte de validació.')
            if triada == '5.3':
                st.write('Les aules tancades afecten les setmanes del 8 i del 15 de març; el canvi d’aula del grup que creix (Transmissió de Calor, grup 21) i les classes que li deixen lloc valen per a tot el semestre.')
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
            with opcions_extra, st.container(key='p2-vista-aula'):
                st.subheader('Consulta una aula')
                aula = tria_si_cal('Aula', aules, key='p2-aula', format_func=lambda a:
                    f'{a} · {base.aules[a].capacitat} places' if a in base.aules else a)
                dades = celles_aula(base, proposta, setmana, aula, noms=noms, relaxacions=relaxacions, referencia=avui)
                st.download_button('Descarrega l’horari d’aquesta aula',
                    exporta_aula_html(base, proposta, setmana, aula, noms=noms, relaxacions=relaxacions,
                        referencia=avui, nom_proposta='Horari d’avui' if triada == 'Avui' else NOMS_PROPOSTES[triada]),
                    file_name=f'horari-{aula.replace("/", "-")}-{triada}-{setmana}.html', mime='text/html')
                st.markdown(taula_html(dades, 'Aula ' + aula, originals=not comparar, estils=False), unsafe_allow_html=True)
        try:
            st.page_link('pagines/imprevistos.py', label='Pas següent: un imprevist →')
        except (KeyError, st.errors.StreamlitAPIException):
            # La pàgina també es pot renderitzar sola, sense st.navigation (proves).
            st.markdown('[Pas següent: un imprevist →](imprevistos)')
        enfoca_pas()
    except Exception:
        mostra_error()

"""Resum de decisió per a la Junta Permanent, sobre el segon semestre."""
from html import escape
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.taules import mostra_taula
from components.vistes import estat
from errors import mostra_error
from nivell2 import junta
from nivell2.base import RESULTATS as SORTIDA, RESULTATS_PRINCIPAL, Proposta
from horaris.check import Informe, _col_loca

RESULTATS = RESULTATS_PRINCIPAL
NOMS_PROPOSTES = {'5.1': 'Aules assignades (5.1)', '5.2': 'Horari complet (5.2)',
                 '5.3': 'Amb imprevistos (5.3)', '5.4': 'Amb el grau nou (5.4)'}


def disponibles():
    noms = {p.parent.name for p in RESULTATS.glob('5.*/proposta.csv')}
    for arrel in (RESULTATS, SORTIDA):
        noms.update(p.parent.name for p in (arrel / 'junta').glob('5.*/junta.json'))
    return ['Avui'] + sorted(noms, key=lambda n: tuple(int(v) for v in n.split('.')))


def ruta_resum(nom):
    rel = Path('junta') / ('junta.json' if nom == 'Avui' else f'{nom}/junta.json')
    return next((r / rel for r in (SORTIDA, RESULTATS) if (r / rel).is_file()), SORTIDA / rel)


def llegeix(path, versio=None):
    try:
        dades = json.loads(Path(path).read_text(encoding='utf-8'))
        return dades if isinstance(dades, dict) else None
    except (OSError, ValueError):
        return None


def empremtes(nom):
    proposta = None if nom == 'Avui' else RESULTATS / nom / 'proposta.csv'
    return junta.empremtes(proposta)


def genera(nom, versio=None, versio_relax=None):
    abans = empremtes(nom)
    escenari = junta.escenari_proposta(nom)
    base = junta.carrega_oficial(escenari)
    model = junta.carrega_model(escenari)
    if nom == 'Avui':
        proposta = Proposta.de_base(base)
        col = _col_loca(base, proposta.a_files(), Informe())
        relax = None
    else:
        path = RESULTATS / nom / 'proposta.csv'
        proposta, col = junta.carrega_proposta(path, base, escenari)
        relax = path.with_name('relaxacions.csv')
        relax = relax if relax.is_file() else None
    dades = junta.calcula(proposta, base, model, col, relax)
    if empremtes(nom) != abans:
        raise ValueError('Les fonts han canviat durant el càlcul')
    dades['empremtes'] = abans
    desti = SORTIDA / 'junta'
    if nom != 'Avui':
        desti /= nom
    junta.escriu_atomic(desti / 'junta.json', json.dumps(dades, ensure_ascii=False, indent=2))
    return dades


def resum_valid(d):
    try:
        assert isinstance(d['excepcions'], list)
        assert isinstance(d['sessions_mogudes'], list)
        assert d['data']
        fitxes(d)
        junta.documents(d)
        return True
    except (KeyError, TypeError, ValueError, AssertionError):
        return False


def carrega(nom):
    anterior = llegeix(ruta_resum(nom))
    try:
        if (anterior and resum_valid(anterior)
                and anterior.get('versio_resum') == junta.VERSIO_RESUM
                and anterior.get('versio_calcul') == junta.VERSIO_CALCUL
                and anterior.get('empremtes') == empremtes(nom)):
            return anterior
        return genera(nom)
    except Exception:
        if anterior and resum_valid(anterior):
            return dict(anterior, avis_actualitzacio=True)
        raise


def grafic_mogudes(files):
    files = sorted(files, key=lambda r: (-r.get('afectades_pct', r['franja_pct']), r['nom']))
    fig = go.Figure(go.Bar(y=[r['nom'] for r in files], x=[r['franja_pct'] for r in files],
        orientation='h', marker_color='#2a78d6',
        text=[f"{junta.percentatge(r['franja_pct'])} · {r['franja']}/{r['sessions']} classes" for r in files],
        textposition='outside', cliponaxis=False,
        hovertemplate='%{y}: %{text}<extra></extra>'))
    fig.update_layout(height=max(260, 38 * len(files) + 80),
        xaxis=dict(title='Classes que canvien de dia o hora (%)', range=[0, 130], ticksuffix=' %'),
        yaxis=dict(autorange='reversed'), margin=dict(l=0, r=120, t=10, b=45))
    return fig


def ocupacio(classes, disponibles):
    marge = disponibles - classes
    if marge < 0:
        return 'vermell', 'Falten aules', 'var(--vermell)'
    if marge == 0:
        return 'ambre', 'Sense marge', '#e8820c'
    return 'verd', 'Hi cap', 'var(--verd)'


def barra(percent, color):
    return (f'<div class="junta-barra"><i style="width:{max(0, min(100, percent)):.2f}%;'
            f'background:{color}"></i></div>')


def files_cursos(files):
    return sorted(files, key=lambda r: (-r.get('afectades_pct', r['franja_pct']), r['nom']))


def barres_cursos(files):
    return ''.join(f'<div class="junta-fila"><span>{escape(r["nom"])}</span>'
                   + barra(r.get('afectades_pct', r['franja_pct']), 'var(--blau)')
                   + f'<b>{junta.percentatge(r.get("afectades_pct", r["franja_pct"]))}</b></div>' for r in files)


def fitxes(d):
    peces = []
    for torn, nom in (('mati', 'Matí'), ('tarda', 'Tarda')):
        p = d['pics'][torn]['pitjor']
        color, text, tinta = ocupacio(p['classes'], p['aules_disponibles'])
        peces.append(f'<section class="junta-fitxa"><h3>{nom}, hora més plena</h3>'
                     f'<div class="junta-xifra">{p["classes"]} <small>de {p["aules_disponibles"]} aules</small></div>'
                     + f'<small>{escape(junta.explicacio_aulari(d))}</small>'
                     + barra(100 * p['classes'] / max(1, p['aules_disponibles']), tinta)
                     + estat({'estat': color, 'etiqueta': text})
                     + ('<small>Si una aula falla, cal fer servir la reserva.</small>'
                        if p['classes'] == p['aules_disponibles'] else '')
                     + ('<small>Estimació de les aules necessàries.</small>' if p['estimacio'] else '')
                     + '</section>')
    cursos = files_cursos(d['sessions_mogudes'])
    pitjor = max(cursos, key=lambda r: r['franja_pct'], default=None)
    if pitjor and pitjor['franja_pct'] == 0:
        pitjor = None
    peces.append('<section class="junta-fitxa"><h3>Curs més afectat</h3>'
                 + (f'<div class="junta-xifra">{junta.percentatge(pitjor["franja_pct"])}</div>'
                    f'<small>{escape(pitjor["nom"])}</small>' if pitjor else '<div class="junta-xifra">Cap</div><small>Cap curs canvia de dia ni d&#39;hora.</small>')
                 + '</section>')
    n = len(d['excepcions'])
    heretades = d['fora_torn_ja_avui']
    peces.append('<section class="junta-fitxa"><h3>Excepcions noves als torns</h3>'
                 f'<div class="junta-xifra">{n} <small>{junta.classe(n)}</small></div>'
                 + estat({'estat': 'ambre' if n else 'verd', 'etiqueta': 'Fora del torn' if n else 'Cap'})
                 + (f'<small>{heretades} {junta.classe(heretades)} ja es {'fa' if heretades == 1 else 'fan'} avui fora del seu torn i no es {'toca' if heretades == 1 else 'toquen'}.</small>' if heretades else '')
                 + '</section>')
    return '<div class="junta-fitxes">' + ''.join(peces) + '</div>'


ESTIL = """<style>
.junta-fitxes{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.junta-fitxa{background:var(--targeta,#fff);border:1px solid var(--linia,#e6e5e0);border-radius:16px;padding:18px;display:flex;flex-direction:column;gap:10px;min-width:0}
.junta-fitxa h3{font-size:14px!important;margin:0;padding:0;color:var(--tinta-2)}
.junta-xifra{font-size:32px;font-weight:700;line-height:1.2}
.junta-xifra small{font-size:15px;font-weight:500}
.junta-fitxa .estat{align-self:flex-start}
.junta-fitxa .estat.ambre,.junta-taula .estat.ambre{background:#fff1e0;color:#9a5200}
.junta-barra{height:8px;background:#eceae4;border-radius:999px;overflow:hidden}
.junta-barra i{display:block;height:100%;border-radius:999px}
.junta-fila{display:grid;grid-template-columns:minmax(0,1fr) minmax(50px,120px) 55px;gap:10px;align-items:center;font-size:14px;padding:6px 0}
.junta-taula{width:100%;border-collapse:collapse;font-size:14px}
.junta-taula td,.junta-taula th{text-align:left;padding:8px 4px;border-bottom:1px solid var(--linia,#e6e5e0)}
.st-key-junta-dos h3{font-size:17px!important}
@media(max-width:900px){.junta-fitxes{grid-template-columns:repeat(2,minmax(0,1fr))}.st-key-junta-dos [data-testid="stHorizontalBlock"]{flex-direction:column}.st-key-junta-dos [data-testid="stColumn"]{width:100%!important;min-width:0!important}}
</style>"""


def mostra():
    st.markdown(ESTIL, unsafe_allow_html=True)
    opcions = disponibles()
    triada = st.selectbox('Proposta', opcions,
                         index=opcions.index('5.2') if '5.2' in opcions else len(opcions)-1,
                         format_func=lambda nom: NOMS_PROPOSTES.get(nom, nom), key='junta-proposta')
    try:
        d = carrega(triada)
        try:
            assert 'fora_torn_ja_avui' in d
            assert 'aulari' in d
            for torn in ('mati', 'tarda'):
                assert 'estimacio' in d['pics'][torn]['pitjor']
                assert all('ocupades_al_pic' in m for m in d['pics'][torn]['mides'])
            assert all('aules_assignades' in r for r in d['sessions_mogudes'])
        except (KeyError, TypeError, AssertionError):
            st.info('Resum antic: cal tornar-lo a generar.')
            return
        if d.get('avis_actualitzacio'):
            from datetime import datetime
            hora = datetime.fromisoformat(d['data']).strftime('%H:%M')
            st.warning(f"Resum de les {hora}; no s'ha pogut actualitzar")
        st.markdown(fitxes(d), unsafe_allow_html=True)
        st.caption(junta.resum_canvis_aula(d))
        for torn, etiqueta in [('mati', 'Matí'), ('tarda', 'Tarda')]:
            pic = d['pics'][torn].get('simultani')
            if pic:
                st.write(f"{etiqueta}: màxim de classes alhora: {pic['classes']} ({pic['hora']}).")
        st.caption(junta.EXPLICACIO_PICS)
        st.caption("Aules ocupades a l’hora punta (per a la reserva): les dues primeres fitxes.")
        if d['excepcions']:
            st.subheader('Excepcions als torns')
            for motiu in dict.fromkeys(e['motiu'] for e in d['excepcions']):
                casos = [e for e in d['excepcions'] if e['motiu'] == motiu]
                noms = sorted({junta.nom(c) for e in casos for c in e['cohorts']})
                st.write(f"{len(casos)} {junta.classe(len(casos))}: {junta.motiu_planer(motiu)} Titulacions: {', '.join(noms)}.")
                if any(e['id_sessio'] == 'S04526' for e in casos):
                    st.write('Cas S04526: ' + junta.MOTIU_S04526)
        format_actual = all('ocupades_al_pic' in m for torn in ('mati', 'tarda')
                            for m in d['pics'][torn]['mides'])
        with st.container(key='junta-dos'):
            esquerra, dreta = st.columns([3, 2])
            with esquerra, st.container(border=True):
                st.subheader("Classes que canvien d’horari o d’aula, per curs")
                cursos = files_cursos(d['sessions_mogudes'])
                if not cursos or cursos[0].get('afectades_pct', cursos[0]['franja_pct']) == 0:
                    st.write("Cap curs canvia de dia ni d'hora.")
                else:
                    st.markdown(barres_cursos(cursos[:8]), unsafe_allow_html=True)
                if len(cursos) > 8 and cursos[0].get('afectades_pct', cursos[0]['franja_pct']) > 0:
                    with st.expander('Veure tots els cursos', expanded=False):
                        st.markdown(barres_cursos(cursos), unsafe_allow_html=True)
            with dreta, st.container(border=True):
                st.subheader("Aules per mida a l'hora més plena")
                torn_triat = st.radio('Torn', ['Matí', 'Tarda'], horizontal=True)
                torn = 'mati' if torn_triat == 'Matí' else 'tarda'
                if format_actual:
                    files = []
                    for m in d['pics'][torn]['mides']:
                        n, total = m['ocupades_al_pic'], m['aules_categoria']
                        color, text = ('vermell', 'Falten') if n > total else ('ambre', 'Just') if n == total else ('verd', 'Hi cap')
                        mida = m.get('mida', str(max(1, m['minim_places'])))
                        files.append(f'<tr><td>{escape(mida)}</td><td>{n} de {total}</td><td>'
                                     + estat({'estat': color, 'etiqueta': text}) + '</td></tr>')
                    st.markdown('<table class="junta-taula"><thead><tr><th>Mida</th><th>Ocupades</th><th>Estat</th></tr></thead><tbody>'
                                + ''.join(files) + '</tbody></table>', unsafe_allow_html=True)
                else:
                    st.info('Resum antic: cal tornar-lo a generar.')
        mostra_taula(pd.DataFrame([{'Titulació i curs': r['nom'],
            'Canvi d’hora': r['franja'], 'Canvi d’aula': r['aula'], 'Aules assignades': r['aules_assignades'],
            'Total afectades': r.get('afectades', r['franja'])}
            for r in files_cursos(d['sessions_mogudes'])]))
        with st.expander('Detall tècnic' , expanded=False):
            st.subheader(junta.titol_marge(d))
            st.write(junta.explicacio_marge(d))
            st.write(d.get('detall_tecnic', junta.DETALL_TECNIC))
            st.write(junta.COM_HO_HEM_CALCULAT)
            st.caption(f"Resum calculat: {d['data']} · {triada}")
            st.caption('Les mides corresponen al moment de més ocupació del torn triat; sense aula assignada, fem servir els alumnes previstos (estimació). Els colors són orientatius i no garanteixen que tot l’horari encaixi.')
            if d['torn_no_avaluable']:
                st.write(f"{d['torn_no_avaluable']} {junta.classe(d['torn_no_avaluable'])} sense torn definit.")
            mostra_taula(pd.DataFrame([{'Titulació i curs': r['nom'], 'Canvien de dia o hora': junta.percentatge(r['franja_pct']), 'Canvis d’aula': r['aula'], 'Aules assignades': r['aules_assignades']} for r in d['sessions_mogudes']]))
            for motiu in dict.fromkeys(r['motiu'] for r in d['excepcions']):
                st.write(junta.motiu_planer(motiu))
            if d['excepcions']:
                mostra_taula(pd.DataFrame([dict(e, motiu=junta.motiu_planer(e['motiu'])) for e in d['excepcions']]))
        if format_actual:
            _, html = junta.documents(d)
            st.download_button('Descarrega el resum A4', html, file_name='junta.html', mime='text/html')
    except Exception:
        mostra_error()

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
from nivell2.base import RESULTATS as SORTIDA

RESULTATS = SORTIDA
NOMS_PROPOSTES = junta.NOMS_PROPOSTES


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
    desti = SORTIDA / 'junta'
    if nom != 'Avui':
        desti /= nom
    return junta.genera(nom, resultats=RESULTATS, sortida=desti)


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
        ref = RESULTATS / '5.2' / 'proposta.csv'
        referencia = junta.empremtes(ref) if nom in ('5.3', '5.4') and ref.is_file() else None
        if (anterior and resum_valid(anterior)
                and anterior.get('versio_resum') == junta.VERSIO_RESUM
                and anterior.get('versio_calcul') == junta.VERSIO_CALCUL
                and anterior.get('empremtes') == empremtes(nom)
                and anterior.get('empremtes_referencia') == referencia):
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
                   + f'<b>{junta.percentatge(r.get("afectades_pct", r["franja_pct"]))}</b></div>' for r in files if r.get('afectades_pct', r['franja_pct']) > 0)


def fitxes(d):
    peces = []
    for torn, nom in (('mati', 'Matí'), ('tarda', 'Tarda')):
        p = d['pics'][torn]['pitjor']
        color, text, tinta = ocupacio(p['classes'], p['aules_disponibles'])
        peces.append(f'<section class="junta-fitxa"><h3>{nom}, hora més plena</h3>'
                     f'<div class="junta-xifra">{p["classes"]} <small>de {p["aules_disponibles"]} aules</small></div>'
                     + barra(100 * p['classes'] / max(1, p['aules_disponibles']), tinta)
                     + estat({'estat': color, 'etiqueta': text})
                     + ('<small>Si una aula falla, cal fer servir la reserva.</small>'
                        if p['classes'] == p['aules_disponibles'] else '')
                     + ('<small>Estimació de les aules necessàries.</small>' if p['estimacio'] else '')
                     + '</section>')
    cursos = files_cursos([r for r in d.get('cursos_afectats', d['sessions_mogudes'])
                                      if r.get('afectades_pct', r['franja_pct']) > 0])
    pitjor = max(cursos, key=lambda r: r['franja_pct'], default=None)
    if pitjor and pitjor['franja_pct'] == 0:
        pitjor = None
    empatats = sum(r['franja_pct'] == pitjor['franja_pct'] for r in cursos) - 1 if pitjor else 0
    torn = ('per passar al torn que els toca' if pitjor and pitjor.get('torn') == pitjor['franja']
            else 'per fer encaixar l’horari')
    peces.append('<section class="junta-fitxa"><h3>Curs més afectat</h3>'
                 + (f'<div class="junta-xifra">{junta.percentatge(pitjor["franja_pct"])}</div>'
                    f'<small>{escape(pitjor["nom"])}</small>'
                    f'<small>de les classes canvien de dia o hora ({pitjor["franja"]} de {pitjor["sessions"]}), {torn}.</small>'
                    + (f'<small>i {empatats} cursos més amb el mateix percentatge.</small>' if empatats else '')
                    if pitjor else '<div class="junta-xifra">Cap</div><small>Cap curs canvia de dia ni d&#39;hora.</small>')
                 + (f'<small>{escape(junta.resum_guany_torn(d))}</small>' if junta.resum_guany_torn(d) else '')
                 + '</section>')
    if 'fora_torn_avui_compten' in d:
        total = d['fora_torn_avui_compten'] + d['fora_torn_avui_heretades']
        peces.append('<section class="junta-fitxa"><h3>Classes fora de torn avui</h3>'
                     f'<div class="junta-xifra">{junta.numero(total)}</div>'
                     f'<small>{junta.numero(total)} = {junta.numero(d["fora_torn_avui_compten"])} que compten'
                     f' + {junta.numero(d["fora_torn_avui_heretades"])} heretades.</small></section>')
    n = len(d['excepcions'])
    heretades = d['fora_torn_ja_avui']
    peces.append('<section class="junta-fitxa"><h3>Excepcions noves als torns</h3>'
                 f'<div class="junta-xifra">{n} <small>{junta.classe(n)}</small></div>'
                 + f'<small>{escape(junta.resum_excepcions(d))}</small>'
                 + estat({'estat': 'ambre' if n else 'verd', 'etiqueta': 'Fora del torn' if n else 'Cap'})
                 + ((f'<small>{heretades} {junta.classe(heretades)} ja es ' + ('fa' if heretades == 1 else 'fan') + ' avui fora del seu torn i no es ' + ('toca' if heretades == 1 else 'toquen') + '.</small>') if heretades else '')
                 + '</section>')
    return ('<div class="junta-fitxes">' + ''.join(peces) + '</div>'
            + f'<p>{escape(junta.explicacio_aulari(d))}</p>'
            + (f'<p>{escape(junta.resum_escenari(d))}</p>' if junta.resum_escenari(d) else ''))


ESTIL = """<style>
.junta-fitxes{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
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
@media(max-width:900px){.st-key-junta-dos [data-testid="stHorizontalBlock"]{flex-direction:column}.st-key-junta-dos [data-testid="stColumn"]{width:100%!important;min-width:0!important}}
</style>"""


def grau_nou_preparat():
    """Consulta el resum existent, sense regenerar ni escriure resultats."""
    d = llegeix(ruta_resum('5.4'))
    if (d and d.get('versio_resum') == junta.VERSIO_RESUM
            and d.get('versio_calcul') == junta.VERSIO_CALCUL
            and d.get('empremtes') == empremtes('5.4')
            and d.get('empremtes_referencia') == empremtes('5.2')):
        return d.get('grau_nou')
    return None


def mostra():
    st.markdown(ESTIL, unsafe_allow_html=True)
    st.write('Aquí tens el resum per decidir: mira les aules ocupades al matí i a la tarda i si hi cap el grau nou. Pots descarregar-lo per a la Junta.')
    espai_conclusio = st.container()
    opcions = disponibles()
    with st.expander('Més opcions', expanded=False):
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
        with espai_conclusio:
            for frase in d.get('conclusio', []):
                st.write(frase)
        st.caption('Proposta: ' + NOMS_PROPOSTES.get(triada, triada))
        st.markdown(fitxes(d), unsafe_allow_html=True)
        if triada == '5.2':
            grau = grau_nou_preparat()
            if grau and grau.get('hi_cap'):
                st.success(f"Hi cap el grau nou de 40 places: {grau['sessions_collocades']} classes col·locades. "
                           f"Classes de l’horari complet que cal moure: {grau['sessions_52_mogudes']}.")
            else:
                st.caption('Consulta la proposta «Amb el grau nou (5.4)» a «Més opcions» per veure’n la cabuda.')
        st.caption(junta.resum_canvis_aula(d))
        if d.get('marge_imprevistos'):
            st.write(junta.explicacio_marge(d))
        if d.get('resum_excepcions_aula'):
            st.write(d['resum_excepcions_aula'])
        for torn, etiqueta in [('mati', 'Matí'), ('tarda', 'Tarda')]:
            pic = d['pics'][torn].get('simultani')
            if pic:
                st.write(f"{etiqueta}: màxim de classes alhora: {pic['classes']} ({pic['hora']}).")
        st.caption(junta.EXPLICACIO_PICS)
        if d['excepcions']:
            st.subheader('Excepcions als torns')
            for motiu in dict.fromkeys(e['motiu'] for e in d['excepcions']):
                casos = [e for e in d['excepcions'] if e['motiu'] == motiu]
                noms = sorted({junta.nom(c) for e in casos for c in e['cohorts']})
                st.write(f"{len(casos)} {junta.classe(len(casos))}: {junta.motiu_planer(motiu)} Titulacions: {', '.join(noms)}.")
        format_actual = all('ocupades_al_pic' in m for torn in ('mati', 'tarda')
                            for m in d['pics'][torn]['mides'])
        with st.container(key='junta-dos'):
            esquerra, dreta = st.columns([3, 2])
            with esquerra, st.container(border=True):
                st.subheader("Classes que canvien d’horari o d’aula, per curs")
                cursos = files_cursos([r for r in d.get('cursos_afectats', d['sessions_mogudes'])
                                      if r.get('afectades_pct', r['franja_pct']) > 0])
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
                        color, text = ('vermell', 'Falten') if m['marge'] < 0 else ('ambre', 'Just') if m['marge'] == 0 else ('verd', 'Hi cap')
                        mida = m.get('mida', str(max(1, m['minim_places'])))
                        files.append(f'<tr><td>{escape(mida)}</td><td>{n} de {total}</td>'
                                     f'<td>{m["demanda_acumulada"]} de {m["oferta_acumulada"]}</td><td>'
                                     + estat({'estat': color, 'etiqueta': text}) + '</td></tr>')
                    st.markdown('<table class="junta-taula"><thead><tr><th>Mida</th><th>Ocupades</th><th>Prou grans</th><th>Estat</th></tr></thead><tbody>'
                                + ''.join(files) + '</tbody></table>', unsafe_allow_html=True)
                    st.caption('Una aula gran pot acollir un grup petit. L’estat compara les classes amb totes les aules prou grans, guardant la reserva.')
                else:
                    st.info('Resum antic: cal tornar-lo a generar.')
        if d.get('mostrar_canvis', triada != 'Avui'):
            mostra_taula(pd.DataFrame([{'Titulació i curs': r['nom'],
                'Canvi d’hora': r['franja'], 'Canvi d’aula': r['aula'], 'Aules assignades': r['aules_assignades'],
                'Total afectades': r.get('afectades', r['franja'])}
                for r in files_cursos(d['sessions_mogudes'])]))
        with st.expander('Detall tècnic' , expanded=False):
            st.subheader(junta.titol_marge(d))
            st.write(junta.explicacio_marge(d))
            st.write(d.get('detall_tecnic', junta.DETALL_TECNIC))
            st.write(junta.COM_HO_HEM_CALCULAT)
            st.caption(f"Resum calculat: {junta.data_planera(d['data'])} · {NOMS_PROPOSTES.get(triada, triada)}")
            st.caption('Les mides corresponen al moment de més ocupació del torn triat; sense aula assignada, fem servir els alumnes previstos (estimació). Els colors són orientatius i no garanteixen que tot l’horari encaixi.')
            if d['torn_no_avaluable']:
                st.write(f"{d['torn_no_avaluable']} {junta.classe(d['torn_no_avaluable'])} sense torn definit.")
            if d.get('mostrar_canvis', triada != 'Avui'):
                mostra_taula(pd.DataFrame([{'Titulació i curs': r['nom'], 'Canvien de dia o hora': junta.percentatge(r['franja_pct']), 'Canvis d’aula': r['aula'], 'Aules assignades': r['aules_assignades']} for r in d['sessions_mogudes']]))
            if d['excepcions']:
                mostra_taula(pd.DataFrame([dict(e, motiu=junta.motiu_planer(e['motiu'])) for e in d['excepcions']]))
        if format_actual:
            _, html = junta.documents(dict(d, proposta=triada))
            st.download_button('Descarrega el resum A4', html, file_name=f'junta-{triada}.html', mime='text/html')
    except Exception:
        mostra_error()
    finally:
        st.write('Pas següent: pregunta-ho a l’Assistent (botó de baix a la dreta)')

"""Un gràfic senzill per resposta; només dades de troballes i inventari."""
from html import escape
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.format import numero
from servei import AULES_DISPONIBLES, AULES_RESERVA, inventari
from presentacio import DIES, context, valor
from textos import PROBLEMES
from components.taules import dades_troballa


def quadrets(t):
    c = context(t)
    ocupades = c.get('pic_n')
    if ocupades is None:
        st.info('El resultat no indica quantes aules es necessiten alhora.')
        return
    icones = ''.join('<i class="' + ('' if n < ocupades else 'l') + '"></i>' for n in range(AULES_DISPONIBLES))
    icones += '<i class="r"></i>' * AULES_RESERVA
    peu = f'{numero(AULES_DISPONIBLES)} aules disponibles: {numero(ocupades)} ocupades al moment més ple i {numero(max(0, AULES_DISPONIBLES - ocupades))} lliures. A part, {numero(AULES_RESERVA)} aules de reserva (vora discontínua).'
    st.markdown(f'<div class="aules" role="img" aria-label="{escape(peu)}">{icones}</div><p class="aules-peu">{escape(peu)}</p>', unsafe_allow_html=True)


def figura(fig, clau):
    fig.update_layout(template='plotly_white', height=fig.layout.height or 350, margin=dict(l=12,r=65,t=35,b=25),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='-apple-system, Segoe UI, system-ui, sans-serif',color='#0b0b0b',size=15),
        separators=',.', showlegend=False, dragmode=False)
    fig.update_xaxes(showgrid=False,zeroline=False,automargin=True,fixedrange=True)
    fig.update_yaxes(showgrid=False,zeroline=False,automargin=True,fixedrange=True)
    st.plotly_chart(fig, key=clau, width='stretch', theme=None, config={'staticPlot':False,'displayModeBar':False,'scrollZoom':False,'doubleClick':False})


def barres(labels, values, clau, unitat=''):
    df = pd.DataFrame({'nom':list(labels),'valor':list(values)}).dropna(subset=['valor'])
    retallat = len(df) > 8
    df = df.sort_values('valor',ascending=False).head(8)
    if df.empty:
        st.info('No hi ha casos per mostrar en aquesta setmana.')
        return
    fig = go.Figure(go.Bar(x=df.valor,y=df.nom,orientation='h',width=.6,marker=dict(color='#2a78d6',cornerradius=4),
        text=[f'{numero(v)}' + (' cas' if v == 1 else ' casos') if unitat == ' casos' else f'{numero(v)}{unitat}' for v in df.valor],textposition='outside',cliponaxis=False,
        hovertemplate='%{y}: %{text}<extra></extra>'))
    fig.update_layout(height=60+36*len(df))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(autorange='reversed',ticks='')
    figura(fig,clau)
    if retallat:
        st.caption('Es mostren els 8 casos amb el valor més alt.')


def planol(t):
    df = t.taula
    if not {'aula','percent_ocupacio'}.issubset(df.columns):
        st.info('No hi ha percentatges per aula disponibles.')
        return
    ocupacio = df[['aula','percent_ocupacio']].drop_duplicates('aula').set_index('aula').percent_ocupacio.to_dict()
    aules = inventari()
    aules = aules[aules.tipus == 'Aules docents'].copy()
    aules['espina'] = aules.aula.str.split('/').str[0]
    aules['planta'] = aules.aula.str.split('/').str[-1].str[0]
    html = '<div class="espines">'
    for espina, grup in aules.groupby('espina',sort=True):
        html += f'<section class="espina"><h3>{escape(espina)}</h3>'
        for planta, sales in grup.groupby('planta',sort=True):
            nom = 'Planta baixa' if planta == '0' else 'Primera planta' if planta == '1' else f'Planta {planta}'
            html += f'<div class="planta">{escape(nom)}</div><div class="rajoles">'
            for r in sales.sort_values('aula').itertuples():
                pct = ocupacio.get(r.aula)
                # Escala absoluta de percentatge: cap ocupació inventada per a les dades absents.
                intensitat = min(1,max(0,float(pct)/100)) if pct is not None else None
                color = '#f1f0ec' if intensitat is None else 'rgb(' + ','.join(str(round(a+(b-a)*intensitat)) for a,b in zip((205,226,251),(24,79,149))) + ')'
                tinta = '#ffffff' if intensitat is not None and intensitat >= .72 else '#000000'
                tip = f'{r.aula} · {numero(r.capacitat)} places · ' + (f'{numero(pct)} % ocupada' if pct is not None else 'ocupació no disponible')
                html += f'<div class="rajola" tabindex="0" title="{escape(tip)}" aria-label="{escape(tip)}" style="background:{color};color:{tinta}"><b>{escape(r.aula)}</b>{escape(numero(r.capacitat))} places<small class="ocupacio-rajola">{escape(numero(pct)) + ' %' if pct is not None else 'Sense dada'}</small></div>'
            html += '</div>'
        html += '</section>'
    st.markdown(html+'</div><p class="escala">Poc ocupada <i></i> Molt ocupada</p>',unsafe_allow_html=True)


def _grafics(t, clau='detall', altres=None):
    df = t.taula
    if t.id == 'hi-cap-mati':
        pic = pd.DataFrame((t.extra or {}).get('pic', df))
        quadrets(t)
        if not {'dia','classes'}.issubset(pic.columns):
            st.info('No hi ha dades diàries disponibles.')
            return
        dies = pic.groupby('dia',sort=False).classes.max().reindex(list(DIES),fill_value=0)
        fig = go.Figure(go.Bar(x=[DIES[d] for d in dies.index],y=dies.values,marker_color='#2a78d6',
            text=[numero(v) for v in dies.values],textposition='outside',cliponaxis=False,
            hovertemplate='%{x}: %{y} aules<extra></extra>'))
        fig.add_hline(y=AULES_DISPONIBLES,line_dash='dash',line_color='#d03b3b',annotation_text=f'{numero(AULES_DISPONIBLES)} aules disponibles')
        fig.update_yaxes(visible=False,range=[0,max(AULES_DISPONIBLES,float(dies.max()))*1.25])
        figura(fig,clau)
        st.caption('Aules necessàries al moment més ple de cada dia. La línia discontínua indica les aules disponibles.')
        return
    if t.id == 'ocupacio':
        planol(t)
        cobertura = (altres or {}).get('hores-aula')
        if cobertura is not None:
            c = context(cobertura)
            st.info(f"Moltes aules semblen buides perquè hi ha sense aula aproximadament {c['proporcio']}. Cal assignar-les abans de donar l’espai per lliure.")
        return
    if df.empty:
        st.info('No hi ha casos per mostrar en aquesta setmana.')
        return
    if t.id == 'marge-grau-nou':
        c = context(t)
        barres(['Hores que necessita el grau nou','Hores lliures al matí'],[c.get('hores_noves_n'),c.get('marge_n')],clau,' h')
        return
    if t.id == 'hores-aula' and {'dia','demanda'}.issubset(df.columns):
        dies = df.groupby('dia',sort=False).demanda.max()
        barres([DIES.get(d,d) for d in dies.index],dies.values,clau,' aules')
        st.caption('Demanda màxima d’aules de cada dia de la setmana seleccionada.')
        return
    etiquetes = {'fora-torn':('cohort','sessions',' classes'), 'aforament':('aula','exces',' alumnes de més'),
        'hores-mortes':('cohort','hores',' h'), 'canvis-aula':('cohort','fora_passadis',' canvis'),
        'dobles-mati':('cohort','sessions',' classes'), 'docents-cavall':('docent','dies_mati_tarda',' dies'),
        'problemes-millores':('problema','xifra',' casos')}
    if t.id not in etiquetes:
        st.info('No hi ha cap comparació disponible per a aquesta resposta.')
        return
    etiqueta,col,unitat = etiquetes[t.id]
    if not {etiqueta,col}.issubset(df.columns):
        st.info('No hi ha dades suficients per dibuixar aquesta comparació.')
        return
    labels = df[etiqueta].astype(str).str.replace(':',' · ',regex=False).str.replace('|',' / ',regex=False)
    if t.id == 'problemes-millores':
        labels = labels.map(lambda nom: PROBLEMES.get(nom, nom))
    values = df[col].map(valor) if col == 'xifra' else pd.to_numeric(df[col],errors='coerce')
    if t.id == 'canvis-aula':
        labels = labels + ' · grup ' + df.subgrup.astype(str)
    if t.id == 'aforament':
        labels = labels + ' · ' + df.dia.map(lambda d:DIES.get(d,d)) + ' ' + df.h_ini.astype(str)
    barres(labels,values,clau,unitat)


def grafics(t, clau='detall', altres=None):
    _grafics(t, clau, altres)
    dades_troballa(t)

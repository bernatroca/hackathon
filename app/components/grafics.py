"""Presentació del contracte sense calcular mètriques de negoci."""
import numbers
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

COLORS = ['#28666E', '#8AA5AD', '#B17555']


def numero(valor):
    if isinstance(valor, numbers.Real) and not isinstance(valor, bool):
        decimals = 0 if float(valor).is_integer() else 2
        return f'{valor:,.{decimals}f}'.translate(str.maketrans({',': '.', '.': ','}))
    return str(valor)


def taula(df):
    formats = {c: numero for c in df.select_dtypes(include='number').columns}
    st.dataframe(df.style.format(formats, na_rep='—'), hide_index=True, width='stretch')


def figura(fig, petit, clau):
    fig.update_layout(template='plotly_white', height=180 if petit else 400, margin=dict(l=12, r=12, t=30, b=25),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        colorway=COLORS, separators=',.', font=dict(color='#24383D'),
        legend=dict(orientation='h', y=-0.25, font=dict(color='#24383D')), barmode='group')
    fig.update_xaxes(tickfont=dict(color='#24383D'), title_font=dict(color='#24383D'), gridcolor='#E2EAEA', linecolor='#D3DFDF', automargin=True)
    fig.update_yaxes(tickfont=dict(color='#24383D'), title_font=dict(color='#24383D'), gridcolor='#E2EAEA', linecolor='#D3DFDF', automargin=True)
    fig.update_annotations(font_color='#24383D')
    st.plotly_chart(fig, width='stretch', key=clau, theme=None, config={'displayModeBar': not petit, 'locale': 'ca'})


def avis(df, text):
    st.warning(text)
    taula(df)


def eix_bloc(df):
    bloc = 'etiqueta' if 'etiqueta' in df else 'bloc' if 'bloc' in df else None
    if bloc is None:
        return None
    return df['dia'].astype(str) + ' · ' + df[bloc].astype(str) if 'dia' in df else df[bloc].astype(str)


def dibuixa(df, tipus, petit=False, clau='grafic', limit=False):
    if not isinstance(df, pd.DataFrame):
        st.warning('Les dades del gràfic no tenen format de taula.')
        return
    if df.empty:
        st.info('No hi ha dades per a aquesta selecció.')
        return
    if tipus == 'taula':
        taula(df)
        return
    if tipus == 'heatmap':
        x = eix_bloc(df)
        if not {'aula', 'dia', 'valor'}.issubset(df.columns) or x is None:
            avis(df, 'El mapa necessita aula, dia, etiqueta o bloc, i valor. Es mostren les dades disponibles.')
            return
        dades = df.copy()
        dades['_columna'] = x
        if dades.duplicated(['aula', '_columna']).any():
            avis(df, 'Hi ha cel·les repetides; cal que el mòdul de dades les resolgui per dibuixar el mapa.')
            return
        sense = dades['aula'].fillna('sense aula').astype(str).str.lower().eq('sense aula')
        dades.loc[sense, 'aula'] = 'sense aula'
        for nom, grup in [('Aules', dades[~sense]), ('Sense aula', dades[sense])]:
            if grup.empty:
                continue
            if nom == 'Sense aula':
                st.caption('Sense aula · sessions pendents d’assignació')
            matriu = grup.pivot(index='aula', columns='_columna', values='valor')
            matriu = matriu.reindex(columns=grup['_columna'].drop_duplicates())
            fig = go.Figure(go.Heatmap(z=matriu.values, x=matriu.columns, y=matriu.index,
                colorscale=[[0, '#F0F4F4'], [1, COLORS[0]]], colorbar=dict(title='Valor'),
                hovertemplate='%{y}<br>%{x}<br>Valor: %{z}<extra></extra>'))
            figura(fig, petit, clau + nom)
        return
    if tipus not in ('barres', 'linia'):
        avis(df, f'Tipus de gràfic desconegut: {tipus}. Es mostra la taula.')
        return
    numeriques = list(df.select_dtypes(include='number').columns)
    categories = [c for c in df.columns if c not in numeriques]
    xcol = categories[0] if categories else df.columns[0]
    x = eix_bloc(df) if limit else None
    if x is None:
        x = df[xcol]
        numeriques = [c for c in numeriques if c != xcol]
    if not numeriques:
        avis(df, 'Falten columnes numèriques per dibuixar el gràfic. Es mostra la taula.')
        return
    hover = x
    if limit:
        x = list(range(len(df)))
    fig = go.Figure()
    for col in numeriques:
        if limit and col != 'classes':
            continue
        trace = go.Bar if tipus == 'barres' else go.Scatter
        fig.add_trace(trace(x=x, y=df[col], name=col.replace('_', ' '),
            **({'customdata': hover, 'hovertemplate': '%{customdata}<br>%{y} classes<extra></extra>'} if limit else {})))
    if limit:
        if 'dia' in df:
            dies = df['dia'].astype(str).reset_index(drop=True)
            fig.update_xaxes(tickmode='array',
                tickvals=[(dies[dies == dia].index[0] + dies[dies == dia].index[-1]) / 2 for dia in dies.drop_duplicates()],
                ticktext=list(dies.drop_duplicates()), title_text='Dia', tickangle=0)
        fig.update_yaxes(title_text='Classes simultànies')
        fig.add_hline(y=19, line_dash='dash', line_color=COLORS[2], annotation_text='19 aules disponibles')
    figura(fig, petit, clau)


def grafics(t, petit=False, clau='troballa'):
    extra = t.extra or {}
    if t.id != 'hi-cap-mati' or ('pic' not in extra and 'per_mida' not in extra):
        dibuixa(t.taula, t.grafic, petit, clau)
        return
    for camp in ('pic', 'per_mida'):
        if camp not in extra or (petit and camp == 'per_mida' and 'pic' in extra):
            continue
        try:
            df = pd.DataFrame(extra[camp])
        except (ValueError, TypeError):
            st.warning(f'No es pot representar «{camp}»: s’esperava una taula o llista de registres.')
            continue
        st.caption('Pic de classes simultànies' if camp == 'pic' else 'Demanda i oferta per mida · hores-aula')
        if camp == 'pic':
            if 'classes' not in df or eix_bloc(df) is None:
                avis(df, 'El pic necessita classes i etiqueta o bloc. Es mostren les dades disponibles.')
            else:
                dibuixa(df, 'linia', petit, clau + camp, limit=True)
        elif {'llindar', 'demanda_h', 'oferta_h', 'oferta_h_amb_seminaris', 'falla'}.issubset(df.columns):
            fig = go.Figure()
            etiquetes = df['llindar'].map(lambda k: f'> {numero(k)} places')
            for i, (col, nom) in enumerate([('demanda_h', 'Demanda'), ('oferta_h', 'Oferta'),
                                           ('oferta_h_amb_seminaris', 'Oferta amb seminaris')]):
                fig.add_bar(x=etiquetes, y=df[col], name=nom, marker_color=COLORS[i])
            for etiqueta, falla in zip(etiquetes, df['falla']):
                if falla is True or str(falla).lower() in ('true', '1'):
                    fig.add_annotation(x=etiqueta, y=1.08, yref='paper', text='Falla', showarrow=False, font_color=COLORS[2])
            fig.update_layout(showlegend=True, legend_title_text='Hores-aula')
            figura(fig, petit, clau + camp)
        else:
            avis(df, 'La comparació per mida necessita llindar, demanda_h, oferta_h, oferta_h_amb_seminaris i falla.')

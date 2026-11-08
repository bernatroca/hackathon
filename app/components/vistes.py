from html import escape
import streamlit as st
from components.grafics import grafics
from mostra import exemples
from presentacio import text, text_portada, abast, desglos, valor, dates_setmana
from servei import una, AULES_DISPONIBLES, AULES_RESERVA
from textos import PROBLEMES
from components.taules import mostra_taula
from errors import mostra_error


def carrega(id_):
    resultat = st.session_state.get('resultats', {})
    if id_ in resultat:
        return resultat[id_]
    try:
        return una(id_, st.session_state.semestre, st.session_state.setmana, st.session_state.versio)
    except KeyError as exc:
        if exc.args != (id_,):
            st.session_state.setdefault('resultats', {})[id_] = None
            mostra_error()
            return None
        return exemples().get(id_)
    except Exception:
        st.session_state.setdefault('resultats', {})[id_] = None
        mostra_error()
        return None


def carrega_grup(ids):
    """Carrega únicament les respostes necessàries per a la pàgina actual."""
    for id_ in ids:
        t = carrega(id_)
        if t is not None:
            st.session_state.resultats[id_] = t


def contingut(t):
    return text(t, st.session_state.get('resultats', {}), setmana_triada=st.session_state.get('setmana'))


def estat(info):
    cami = {'vermell': '<path d="m5 5 6 6m0-6-6 6"/>',
            'ambre': '<path d="M8 4v5m0 2v1"/>',
            'verd': '<path d="m4.5 8 2.5 2.5 4.5-5"/>'}[info['estat']]
    svg = f'<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><circle cx="8" cy="8" r="7" fill="currentColor"/><g fill="none" stroke="#fff" stroke-width="2">{cami}</g></svg>'
    return f'<span class="estat {info["estat"]}">{svg}<span class="estat-text">{escape(info["etiqueta"])}</span></span>'


def mostra_avis(t):
    if (t.extra or {}).get('mostra'):
        st.warning('MOSTRA · Dades fictícies; no són resultats del repte.')


def obre(t):
    if st.button('Com ho sabem →',key='obre-'+t.id):
        st.session_state.detall_id = t.id
        st.query_params['resposta'] = t.id
        st.rerun()


def heroi(t):
    info = text_portada(t, contingut(t))
    with st.container(key='heroi'):
        mostra_avis(t)
        esquerra,dreta = st.columns([1.7,1],gap='medium',vertical_alignment='center')
        with esquerra:
            st.markdown(f'<h2 class="pregunta" data-estat="{info["estat"]}">{escape(info["titol"])}</h2>',unsafe_allow_html=True)
            st.markdown(estat(info), unsafe_allow_html=True)
            st.subheader(info['c']['resposta'])
            st.markdown(f'<p class="frase-heroi">{escape(info["frase"])}</p>',unsafe_allow_html=True)
            obre(t)
        with dreta:
            ocupades = info['c'].get('pic_n')
            if ocupades is None:
                st.info('No s’ha indicat el pic d’aules.')
            else:
                icones = ''.join('<i class="' + ('' if n < ocupades else 'l') + '"></i>'
                    for n in range(AULES_DISPONIBLES)) + '<i class="r"></i>' * AULES_RESERVA
                peu = f'{ocupades} ocupades · {max(0, AULES_DISPONIBLES - ocupades)} lliures · {AULES_RESERVA} de reserva'
                st.markdown(f'<figure class="aules-portada"><div class="aules" role="img" aria-label="Aules: {escape(peu)}">'
                    f'{icones}</div><figcaption>{escape(peu)}</figcaption></figure>',unsafe_allow_html=True)


def resum_grau(info):
    c = info['c']
    return (f'<div class="resum-grau"><p><span class="xifra-targeta">{escape(c["hores_noves"])} h</span> a la setmana que necessita</p>'
        f'<p><strong>{escape(c["hores_lliures"])} h</strong> lliures {escape(c["etiqueta_setmana"])}</p>'
        '</div>')


def frase_grau(t, info):
    """Reutilitza la frase calculada amb els recomptes del servei."""
    return info['frase']


def targeta(t, posicio=0):
    complet = contingut(t)
    info = text_portada(t, complet)
    with st.container(border=True, key='targeta-'+t.id):
        mostra_avis(t)
        st.markdown(f'<article class="targeta-cor"><h2>{escape(info["titol"])}</h2>'
            f'<div class="xifra-targeta">{escape(info["c"]["xifra"])}</div>'
            f'<p class="frase-targeta">{escape(info["frase"])}</p>{estat(info)}</article>',unsafe_allow_html=True)
        with st.container(key='peu-targeta-'+t.id):
            st.markdown(f'<p class="proposem"><b>Proposem</b><br>{escape(info["proposem"])}</p>', unsafe_allow_html=True)
            obre(t)


def detall(t):
    if t is None:
        st.info('Aquesta resposta encara no està disponible.')
        return
    info = contingut(t)
    mostra_avis(t)
    st.markdown(estat(info),unsafe_allow_html=True)
    st.header(info['titol'])
    resposta = info['c'].get('resposta',info['c']['xifra'])
    st.markdown(resum_grau(info) if t.id == 'marge-grau-nou' else f'<div class="xifra-targeta resposta-gran">{escape(resposta)}</div>',unsafe_allow_html=True)
    st.caption(('Semestre complet · Desglossament per titulació i curs.' if t.id == 'fora-torn' else
                abast(t) + ' · La xifra principal resumeix el semestre; la comparació mostra la setmana seleccionada.')
               if t.id != 'marge-grau-nou' else abast(t) + ' · Comparació de les hores necessàries i lliures de la mateixa setmana.')
    grafics(t,clau='detall-'+t.id,altres=st.session_state.get('resultats',{}))
    st.subheader('Què vol dir')
    st.write(info['frase'])
    if t.id == 'hi-cap-mati':
        if info['c'].get('coll_ampolla'):
            st.write(info['c']['coll_ampolla'])
        parts = [('Setmana amb més classes alhora: ' if st.session_state.get('setmana') is None else 'Setmana seleccionada: ')
            + dates_setmana((t.extra or {}).get('setmana'))]
        torns = (t.extra or {}).get('torns')
        if torns is not None and 'setmana_pitjor' in torns:
            parts.append('setmana amb més ocupació de cada torn: ' + ', '.join(f"{'matí' if r.torn == 'mati' else r.torn} {dates_setmana(r.setmana_pitjor)}" for r in torns.itertuples()))
        st.caption(' · '.join(parts) + (' · Horari validat amb el verificador oficial.' if info['c'].get('validat')
            else ' · Cal validar que les classes es poden repartir en un horari.'))
    if t.id == 'hores-aula':
        if desglos(t.extra):
            st.write(desglos(t.extra))
        hores = t.extra.get('hores_per_torn')
        if hores is not None:
            st.subheader('Hores d’aula per torn')
            mostra_taula(hores.rename(columns={'franja': 'torn'}))
            st.caption('Setmana indicada, amb tots els cursos: hores d’aula necessàries i oferta de les 19 aules. L’oferta és nominal, abans de descomptar festius i aturades.')
        elif 'hores_demanda' in t.extra and 'hores_disponibles' in t.extra:
            from components.format import numero
            st.write(f"Setmana indicada: {numero(t.extra['hores_demanda'])} h d’aula necessàries / {numero(t.extra['hores_disponibles'])} h disponibles.")
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
    with st.expander('Detalls informàtics: consulta SQL',expanded=False):
        st.write(t.metode)
        st.code(t.sql,language='sql')
        # No mostrem identificadors de sessió: la consulta SQL permet reproduir la xifra.
        st.caption('Per comprovar la xifra, executa aquesta consulta sobre les dades del repte.')


def detall_obert():
    id_ = st.query_params.get('resposta') or st.session_state.get('detall_id')
    if not id_:
        return False
    if st.button('← Torna',key='torna'):
        st.session_state.detall_id = None
        st.query_params.pop('resposta', None)
        st.rerun()
    detall(carrega(id_))
    return True


def franja_context(semestre, setmana, tipica=None):
    nom = '2n' if semestre == 2 else '1r'
    etiqueta = 'setmana típica' if setmana is None else 'setmana'
    referencia = setmana or tipica
    valor = dates_setmana(referencia)
    if isinstance(referencia, (tuple, list)) and len(referencia) >= 3:
        from components.format import numero
        valor += f' · {numero(referencia[2])} classes'
    return f'<div class="franja-context"><strong>{nom} semestre</strong> · <strong>{etiqueta}</strong> {escape(valor)}</div>'


def estil_respostes():
    """Regles locals: la portada i les altres parts no hereten aquests retocs."""
    st.markdown('''<style>
.st-key-respostes {container-type:inline-size;container-name:respostes;}
.st-key-respostes .st-key-graella-respostes [data-testid="stHorizontalBlock"] {
 display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;align-items:stretch;
}
.st-key-respostes .st-key-graella-respostes [data-testid="stColumn"] {
 width:100%!important;min-width:0!important;display:flex;flex-direction:column;height:100%;
}
.st-key-respostes .st-key-graella-respostes [data-testid="stColumn"] > [data-testid="stVerticalBlock"],
.st-key-respostes [data-testid="stLayoutWrapper"]:has(> [class*="st-key-resposta-compacta-"]) {
 display:flex;flex-direction:column;flex:1 1 auto;height:100%;min-width:0;
}
.st-key-respostes [class*="st-key-resposta-compacta-"] {
 display:flex;flex-direction:column;flex:1 1 auto;height:100%;background:var(--targeta,#fff);border-radius:16px;
}
.st-key-respostes .resposta-compacta {display:flex;flex-direction:column;gap:8px;min-width:0;}
.st-key-respostes .resposta-compacta .estat {margin:0;align-self:flex-start;}
.st-key-respostes .resposta-compacta h2 {
 font-size:18px!important;line-height:1.3;margin:0;min-height:2.6em;
}
.st-key-respostes .xifra-compacta {font-size:28px;font-weight:700;line-height:1.2;overflow-wrap:anywhere;}
.st-key-respostes .frase-compacta {
 margin:0;font-size:16px;line-height:1.5;color:#52514e;white-space:normal;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden;
}
.st-key-respostes [data-testid="stLayoutWrapper"]:has(> [class*="st-key-enllac-resposta-"]),
.st-key-respostes [class*="st-key-enllac-resposta-"] {margin-top:auto;flex:0 0 auto;}
.st-key-respostes button[kind="secondary"] {color:#256abf;border:0;background:transparent;padding-left:0;}
.st-key-respostes .recompte {font-size:16px;white-space:nowrap;margin:0;padding-top:30px;}
/* El filtre d'estat fa servir els colors i les icones de les pastilles de les targetes. */
.st-key-respostes-estat [role=toolbar] > button::before {content:'';width:16px;height:16px;flex:none;margin-right:6px;background:center/16px no-repeat;}
.st-key-respostes-estat [role=toolbar] > button {display:inline-flex;align-items:center;font-weight:600;}
.st-key-respostes-estat [role=toolbar] {flex-wrap:wrap;overflow:visible;row-gap:8px;}
.st-key-respostes-estat [role=toolbar] > button[aria-pressed=false] {background:#fff;color:#52514e;border-color:#e6e5e0;}
.st-key-respostes-estat [role=toolbar] > button[aria-pressed=false]::before {filter:grayscale(1);opacity:.55;}
.st-key-respostes-estat [role=toolbar] > button:nth-of-type(1)::before {background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='7' fill='%23a12c2c'/%3E%3Cg fill='none' stroke='white' stroke-width='2'%3E%3Cpath d='m5 5 6 6m0-6-6 6'/%3E%3C/g%3E%3C/svg%3E");}
.st-key-respostes-estat [role=toolbar] > button:nth-of-type(1)[aria-pressed=true] {background:#fbe9e9;color:#a12c2c;border-color:#fbe9e9;}
.st-key-respostes-estat [role=toolbar] > button:nth-of-type(2)::before {background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='7' fill='%238a5c00'/%3E%3Cg fill='none' stroke='white' stroke-width='2'%3E%3Cpath d='M8 4v5m0 2v1'/%3E%3C/g%3E%3C/svg%3E");}
.st-key-respostes-estat [role=toolbar] > button:nth-of-type(2)[aria-pressed=true] {background:#fff5dc;color:#8a5c00;border-color:#fff5dc;}
.st-key-respostes-estat [role=toolbar] > button:nth-of-type(3)::before {background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='7' fill='%231f6b33'/%3E%3Cg fill='none' stroke='white' stroke-width='2'%3E%3Cpath d='m4.5 8 2.5 2.5 4.5-5'/%3E%3C/g%3E%3C/svg%3E");}
.st-key-respostes-estat [role=toolbar] > button:nth-of-type(3)[aria-pressed=true] {background:#e9f4ec;color:#1f6b33;border-color:#e9f4ec;}
@container respostes (max-width:850px) {
 .st-key-respostes .st-key-graella-respostes [data-testid="stHorizontalBlock"] {grid-template-columns:repeat(2,minmax(0,1fr));}
}
@container respostes (max-width:480px) {
 .st-key-respostes .st-key-graella-respostes [data-testid="stHorizontalBlock"] {grid-template-columns:minmax(0,1fr);}
 .st-key-respostes .st-key-filtres-respostes [data-testid="stHorizontalBlock"] {flex-direction:column;}
 .st-key-respostes .st-key-filtres-respostes [data-testid="stColumn"] {width:100%!important;flex:1 1 100%!important;}
 .st-key-respostes .recompte {padding-top:0;}
}
</style>''',unsafe_allow_html=True)


def targeta_compacta(t, info=None):
    info = contingut(t) if info is None else info
    if t.id == 'marge-grau-nou':
        info = dict(info, frase=(f"{info['c']['hores_noves']} h a la setmana; "
            f"{info['c']['hores_lliures']} h lliures {info['c']['etiqueta_setmana']}."))
    with st.container(border=True,height='stretch',key='resposta-compacta-'+t.id):
        mostra_avis(t)
        st.markdown(f'<article class="resposta-compacta" data-resposta="{escape(t.id)}">'
            f'{estat(info)}<h2>{escape(info["titol"])}</h2>'
            f'<div class="xifra-compacta">{escape(str(info["c"]["xifra"]))}</div>'
            f'<p class="frase-compacta" title="{escape(info["frase"])}">{escape(info["frase"])}</p></article>',unsafe_allow_html=True)
        with st.container(key='enllac-resposta-'+t.id):
            obre(t)

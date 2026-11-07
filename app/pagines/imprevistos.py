"""Imprevistos sobre l'horari proposat; admet dades inventades injectades."""
import csv
import hashlib
from html import escape
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from components.vistes import estat
from nivell2.imprevistos import ORDRE, calcula


def normalitza_assignatura(text):
    """Repara mojibake UTF-8/Latin-1 habitual i uniformitza apòstrofs."""
    if not isinstance(text, str):
        return text
    reparat = text
    # Repetim per arreglar casos de doble codificació, però només si millora.
    for _ in range(2):
        try:
            candidat = reparat.encode('cp1252').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        def qualitat(s):
            return sum(s.count(x) for x in ('Ã', 'â€', 'Â', '\ufffd')) + sum(
                1 for c in s if '\x80' <= c <= '\x9f')
        if qualitat(candidat) >= qualitat(reparat):
            break
        reparat = candidat
    # C1 0x92 acostuma a ser l'apòstrof tipogràfic en CP1252 llegit com Latin-1.
    reparat = reparat.replace('\x92', '’')
    reparat = reparat.replace('â€™', '’').replace('â', '’')
    return reparat.replace("'", '’').replace('`', '’').replace('´', '’')


CSS = """<style>
.st-key-imp-pagina{gap:20px;min-width:0;}
.st-key-imp-pagina .imp-intro{color:var(--tinta-2);margin:0;}
.st-key-imp-pagina .imp-resum{background:var(--targeta);border:1px solid var(--linia);border-radius:16px;padding:20px;}
.st-key-imp-pagina .imp-resum p{margin:4px 0 16px;color:var(--tinta-2);}
.st-key-imp-pagina .imp-xifres{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;}
.st-key-imp-pagina .imp-xifres b{display:block;font-size:30px;line-height:1.2;}
.st-key-imp-pagina .imp-xifres span{font-size:15px;color:var(--tinta-2);}
.st-key-imp-pagina .imp-targetes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;}
.st-key-imp-pagina .imp-targeta{background:var(--targeta);border:1px solid var(--linia);border-radius:16px;padding:22px;display:flex;flex-direction:column;gap:12px;min-width:0;overflow-wrap:anywhere;}
.st-key-imp-pagina .imp-targeta h3{font-size:20px!important;margin:0;padding:0;}
.st-key-imp-pagina .imp-targeta p{margin:0;color:var(--tinta-2);}
.st-key-imp-pagina .imp-targeta .imp-accio{border-top:1px solid var(--linia);padding-top:12px;}
.st-key-imp-pagina .imp-targeta .estat{margin-top:auto;margin-bottom:0;white-space:normal;}
.st-key-imp-pagina .estat.ambre{background:#fff1e0;color:#9a5200;}
.st-key-imp-filtres [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:8px;}
.st-key-imp-filtres [data-testid="stColumn"]{flex:0 1 auto!important;width:auto!important;min-width:0!important;}
.st-key-imp-filtres button{border-radius:999px;padding:6px 12px;min-height:34px;background:var(--targeta);color:var(--tinta);border:1px solid var(--linia);}
.st-key-imp-filtres button p{font-size:14px;}
.st-key-imp-filtres button[kind="primary"]{background:var(--blau-clar);border-color:var(--blau);font-weight:600;}
.st-key-imp-filtres button:focus-visible{outline:2px solid var(--blau);outline-offset:2px;}
@container contingut (max-width:650px){
 .st-key-imp-pagina .imp-targetes{grid-template-columns:minmax(0,1fr);}
 .st-key-imp-pagina .imp-xifres{grid-template-columns:minmax(0,1fr);gap:12px;}
}
@media(max-width:650px){
 .st-key-imp-pagina .imp-targetes,.st-key-imp-pagina .imp-xifres{grid-template-columns:minmax(0,1fr);}
 .st-key-imp-pagina .imp-targeta{padding:18px;}
}
</style>"""


def _fitxers():
    # Importació diferida: la prova amb dades injectades no necessita el paquet.
    from nivell2.base import RESULTATS_PRINCIPAL
    abans, despres = RESULTATS_PRINCIPAL / '5.2', RESULTATS_PRINCIPAL / '5.3'
    return (abans / 'proposta.csv', despres / 'proposta.csv',
            abans / 'relaxacions.csv', despres / 'relaxacions.csv', despres / 'informe.json',
            despres / 'resum.json')


def _informe_validat(path, proposta):
    informe = json.loads(path.read_text(encoding='utf-8'))
    sha = hashlib.sha256(proposta.read_bytes()).hexdigest()
    if informe.get('context', {}).get('proposta_sha256') != sha:
        raise ValueError('L’informe oficial no correspon al CSV actual.')
    return informe


def _llegeix_relaxacions(path):
    if not path.is_file():
        return []
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


@st.cache_data(show_spinner=False)
def _carrega(paths, versions):
    """Les versions dels resultats invaliden la memòria cau en regenerar-los."""
    from nivell2.base import CONTINGENCIES, PAQUET, Proposta, carrega_oficial
    abans, despres, relax_abans, relax_despres, informe_path, resum = map(Path, paths)
    informe = _informe_validat(informe_path, despres)
    with (PAQUET / 'activitats.csv').open(encoding='utf-8-sig', newline='') as f:
        noms = {r['codi']: r['assignatura'] for r in csv.DictReader(f)}
    return calcula(carrega_oficial(), carrega_oficial(CONTINGENCIES),
                   Proposta.llegeix(abans), Proposta.llegeix(despres),
                   _llegeix_relaxacions(relax_despres),
                   relaxacions_referencia=_llegeix_relaxacions(relax_abans),
                   resum=json.loads(resum.read_text(encoding='utf-8')) if resum.is_file() else {},
                   informe=informe, noms=noms)


def carrega():
    paths = _fitxers()
    if not paths[1].is_file():
        return None
    # Només un informe oficial corresponent al CSV permet mostrar un veredicte.
    if not paths[0].is_file() or not paths[4].is_file():
        raise ValueError('La proposta és incompleta.')
    return _carrega(tuple(map(str, paths)),
                    tuple((p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
                          if p.is_file() else None for p in paths))


def veredicte(resum):
    valor = resum.get('veredicte', '')
    if valor in ('VALIDA', 'VALIDA AMB RELAXACIONS DECLARADES'):
        return 'verd', 'Comprovat amb el verificador oficial'
    if valor in ('NO VALIDA', 'INVALIDA'):
        return 'vermell', 'La proposta no supera la comprovació oficial'
    return 'ambre', 'Pendent de comprovació oficial'


def quantitat(n):
    return str(n) if n else 'cap'


def classes_afectades(n):
    return f'{quantitat(n)} {"classe afectada" if n <= 1 else "classes afectades"}'


def accio(aula, franja):
    return (f'Què hem fet: {quantitat(aula)} {"canvia" if aula <= 1 else "canvien"} '
            f'd’aula i {quantitat(franja)} de dia o hora.')


def suport(n):
    return (f'{quantitat(n)} {"classe més es mou" if n <= 1 else "classes més es mouen"} '
            'per fer lloc a les afectades.')


def resum_html(resum):
    color, text = veredicte(resum)
    temps = resum.get('temps_s')
    durada = (f'en {temps:.2f} {"segon" if temps == 1 else "segons"}'.replace('.', ',')
              if temps is not None else 'Temps no disponible')
    xifres = []
    for clau, canvi in (('canvis_aula_vs_referencia', 'd’aula'),
                        ('canvis_franja_vs_referencia', 'de dia o hora')):
        n = resum[clau]
        etiqueta = ('classe canvia' if n <= 1 else 'classes canvien') + ' ' + canvi
        xifres.append((quantitat(n), etiqueta))
    xifres.append((durada, 'temps de càlcul'))
    excepcions = (' Amb les excepcions declarades.'
                  if resum.get('veredicte') == 'VALIDA AMB RELAXACIONS DECLARADES' else '')
    oficials = resum.get('canvis_aula_oficials')
    recuperades = resum.get('canvis_aula_recuperades', 0)
    nota = ''
    if (oficials is not None and recuperades
            and resum['canvis_aula_vs_referencia'] == oficials+recuperades):
        nota = (f'<p>El CSV inclou {resum["canvis_aula_vs_referencia"]} canvis d’aula. '
                f'El verificador en compta {oficials}: no compta el canvi d’aula '
                'de la classe cancel·lada que recuperem.</p>')
    return ('<section class="imp-resum" aria-label="Resum de la proposta">'
            + estat({'estat': color, 'etiqueta': text})
            + '<p>Canvis respecte de l’horari proposat.' + excepcions + '</p>'
            + '<div class="imp-xifres">'
            + ''.join(f'<div><b>{escape(str(n))}</b> <span>{etiqueta}</span></div>' for n, etiqueta in xifres)
            + '</div>' + nota + '</section>')


def targetes_html(targetes, validada=True):
    peces = []
    for t in targetes:
        color = 'ambre' if t['excepcio'] else 'verd'
        text = 'Resolt amb excepció' if t['excepcio'] else 'Resolt'
        if not validada:
            color, text = 'ambre', 'Pendent de comprovació'
        peces.append('<article class="imp-targeta">'
                     f'<h3>{escape(t["titol"])}</h3><p>{escape(t["descripcio"])}</p>'
                     f'<p><strong>{classes_afectades(t["sessions_afectades"])}</strong></p>'
                     f'<p class="imp-accio">{accio(t["canvis_aula"], t["canvis_franja"])}</p>'
                     + ''.join(f'<p>{escape(m)}</p>' for m in t['motius'])
                     + estat({'estat': color, 'etiqueta': text}) + '</article>')
    return '<div class="imp-targetes">' + ''.join(peces) + '</div>'


def _selecciona(clau):
    st.session_state['imp-filtre'] = clau


def mostra_filtres(dades):
    opcions = [('totes', 'Tots els imprevistos')]
    opcions.extend((t['clau'], t['titol']) for t in dades['imprevistos'])
    if any(not r['imprevistos'] for r in dades['files']):
        opcions.append(('suport', 'Altres classes mogudes'))
    actiu = st.session_state.get('imp-filtre', 'totes')
    if actiu not in dict(opcions):
        actiu = 'totes'
    with st.container(key='imp-filtres'):
        for columna, (clau, nom) in zip(st.columns(len(opcions)), opcions):
            n = len(filtra(dades['files'], clau))
            columna.button(f'{nom} ({quantitat(n)})', key='imp-boto-' + clau,
                           type='primary' if actiu == clau else 'secondary',
                           on_click=_selecciona, args=(clau,))
    return actiu


def filtra(files, clau):
    return [r for r in files if clau == 'totes' or clau in r['imprevistos']
            or (clau == 'suport' and not r['imprevistos'])]


def mostra(dades=None):
    """La navegació posa el títol; la prova autònoma també el posa abans."""
    with st.container(key='imp-pagina'):
        st.markdown(CSS, unsafe_allow_html=True)
        try:
            if dades is None:
                dades = carrega()
            if dades is None:
                st.info('Encara no hi ha la proposta d’imprevistos')
                st.code(ORDRE, language='bash')
                return
            resum = dades['resum']
            st.markdown('<p class="imp-intro">Partim de l’horari proposat i recol·loquem '
                        'les classes afectades. ' + suport(resum.get('classes_de_suport', 0))
                        + '</p>', unsafe_allow_html=True)
            st.markdown(resum_html(resum), unsafe_allow_html=True)
            st.markdown(targetes_html(dades['imprevistos'], veredicte(resum)[0] == 'verd'),
                        unsafe_allow_html=True)
            st.subheader('Què canvia')
            st.caption('Una fila per classe datada, ordenada pel dia i l’hora d’abans. '
                       'Una classe pot estar afectada per més d’un imprevist.')
            if resum.get('classes_de_suport', 0):
                st.caption(suport(resum['classes_de_suport']))
            clau = mostra_filtres(dades)
            files = filtra(dades['files'], clau)
            if files:
                st.dataframe(pd.DataFrame([{'Assignatura': normalitza_assignatura(r['assignatura']), 'Grup': r['grup'],
                                           'Abans': r['abans'], 'Després': r['despres']} for r in files]),
                             hide_index=True, width='stretch')
            else:
                st.info('No hi ha classes que canviïn amb aquest filtre.')
            with st.expander('Detall tècnic', expanded=False):
                st.write('Excepcions declarades per motiu, incloses les que ja tenia l’horari proposat:')
                relaxacions = resum.get('relaxacions_per_motiu', [])
                if relaxacions:
                    st.dataframe(pd.DataFrame([{'Motiu': r['motiu'], 'Classes': r['sessions']}
                                               for r in relaxacions]), hide_index=True, width='stretch')
                else:
                    st.write('No hi ha excepcions declarades.')
                st.write('Per tornar a generar la proposta, des de l’arrel del projecte:')
                st.code(dades.get('ordre', ORDRE), language='bash')
        except Exception:
            # No mostrem excepcions de lectura que podrien incloure contingut privat.
            st.error('No hem pogut carregar la proposta d’imprevistos. Torna-la a generar i actualitza les dades.')
            st.code(ORDRE, language='bash')


if __name__ == '__main__':
    mostra()

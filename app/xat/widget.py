"""Widget persistent al document principal de Streamlit 1.67."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from uuid import uuid4

if sys.version_info < (3, 10):
    raise RuntimeError('L’assistent necessita Python 3.10 o més nou. Executa l’app amb l’entorn virtual del projecte.')

import streamlit as st

WEB = Path(__file__).with_name('web')
PREGUNTES = {
    'Com estem avui': ['Quantes sessions són al torn equivocat?', 'Quina aula va més plena?', 'Si 1r i 2n fan classe al matí, hi cabem?'],
    'Horari proposat': ['On té classe aquest grup dimarts?', 'Què ha canviat respecte d’avui?', 'Quines classes d’aquest grup canvien de dia o hora i per què?'],
    'Imprevistos': ['Quines classes afecta l’avaria de la Q1/1003 el 10/03?', 'Redacta l’avís per al grup 21 de Transmissió de Calor', 'Què passa si l’aula Q2/1009 s’avaria dijous 11/03?'],
    'Resum per a la Junta': ['Resumeix aquesta proposta en tres frases per a la Junta', 'Quin risc té aquesta proposta?'],
    'Totes les respostes': ['Quantes classes no tenen aula assignada?', 'Quantes classes tenen més alumnes que places?'],
}
PER_DEFECTE = ['Quantes classes no tenen aula assignada?', 'Quines propostes d’horari hi ha?']


def _imprevistos():
    # El mateix carregador i la mateixa memòria cau que la pàgina del 5.3.
    from pagines.imprevistos import carrega
    dades = carrega()
    return [t['descripcio'] for t in dades['imprevistos']] if dades else []


def _nom_proposta(proposta, junta=False):
    if junta:
        from pagines.junta import NOMS_PROPOSTES
    else:
        from pagines.part2 import NOMS_PROPOSTES
    return NOMS_PROPOSTES.get(proposta, str(proposta))


def _api():
    # Import diferit: el backend pot no estar integrat encara. arrenca és
    # idempotent i comprova a cada renderitzat que el servidor continua viu.
    from xat import servidor
    url = servidor.arrenca().rstrip('/')
    return url if url.endswith('/api/xat') else url + '/api/xat'


def pantalla_actual(titol, estat):
    """Context visible de la pàgina, sense consultes ni files de sessions."""
    parts = [titol]
    semestre = estat.get('semestre', 2)
    setmana = estat.get('setmana')
    linies = [f'Està mirant «{titol}».']
    preguntes = PREGUNTES.get(titol, PER_DEFECTE)
    if titol == 'Horari proposat':
        semestre = 2  # La graella és sempre del segon semestre.
        setmana = estat.get('p2-setmana')
        proposta = estat.get('p2-proposta', 'Avui') if estat.get('p2-vista') == 'Proposta i avui' else 'Avui'
        parts.append(_nom_proposta(proposta))
        linies.append(f'Compara la proposta {proposta} amb avui.' if proposta != 'Avui' else 'Mostra només l’horari d’avui.')
        grup = ' '.join(str(estat[k]) for k in ('p2-titulacio', 'p2-curs', 'p2-grup') if estat.get(k) is not None)
        if grup:
            parts.append(grup)
            linies.append(f'Estudis, curs i grup seleccionats: {grup}.')
        if estat.get('p2-aula'):
            linies.append(f'Aula seleccionada a la vista per aula: {estat["p2-aula"]}.')
        if proposta == 'Avui':
            preguntes = ['On té classe aquest grup dimarts?', 'Quines aules fa servir aquest grup?']
    elif titol == 'Resum per a la Junta':
        semestre = 2
        proposta = estat.get('junta-proposta', 'Avui')
        parts.append(_nom_proposta(proposta, junta=True))
        linies.append(f'Proposta seleccionada: {proposta}.')
    elif titol == 'Imprevistos':
        semestre = 2
        linies.append('Mostra els imprevistos de la proposta 5.3.')
    if titol in ('Imprevistos', 'Resum per a la Junta'):
        linies.append(f'Semestre {semestre}.')
        if titol == 'Resum per a la Junta':
            linies.append('Escenari d’imprevistos de la proposta 5.3 (només s’aplica al 5.3):')
        try:
            imprevistos = _imprevistos()
        except Exception:
            imprevistos = []
        linies.extend(imprevistos or ['El detall dels imprevistos del 5.3 no està disponible ara mateix.'])
    else:
        linies.append(f'Semestre {semestre}. Setmana: {setmana if setmana is not None else "típica"}.')
    if titol in ('Com estem avui', 'Totes les respostes'):
        if titol == 'Com estem avui':
            linies.append('La pàgina diu: Sí, hi cap; confirmat amb l’horari proposat (5.2) '
                          'i el verificador oficial; pic 15 de 19 aules (segon semestre).')
        detall_id = estat.get('detall_id')
        if detall_id:
            from textos import TEXTOS
            detall = estat.get('resultats', {}).get(detall_id)
            nom = getattr(detall, 'titol', None) or TEXTOS.get(detall_id, {}).get('titol', detall_id)
            parts.append(nom)
            linies.append(f'Resposta oberta: «{nom}» (identificador: {detall_id}).')
            preguntes = ['Explica’m aquesta resposta en paraules senzilles', 'Què es pot millorar en aquest cas?']
    return dict(resum=' · '.join(parts), text='\n'.join(linies),
                preguntes=preguntes)


def _json(valor):
    # El context és dada: no pot tancar el script ni executar HTML.
    return json.dumps(valor, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def posa_widget(pantalla: dict | None = None):
    try:
        api = _api()
    except Exception:
        # El GET de salut del widget desactiva l'enviament sense cap port.
        api = 'data:application/json,' + '%7B%22teClau%22%3Afalse%7D'
    opcions = dict(api=api, titol='Assistent',
                   salutacio='Pregunta’m sobre l’horari, les aules o les propostes de l’Escola.',
                   preguntes=PER_DEFECTE)
    css = (WEB / 'xat-ia.css').read_text()
    js = (WEB / 'xat-ia.js').read_text()
    # Els nodes viuen al document, fora del cicle de vida dels blocs Streamlit.
    # El nonce força l'execució també quan el context no ha canviat.
    st.html(f'''<script>
// render {uuid4().hex}
(() => {{
  if (!document.getElementById('xatia-estil')) {{
    const estil = document.createElement('style');
    estil.id = 'xatia-estil'; estil.textContent = {_json(css)};
    document.head.appendChild(estil);
  }}
  if (!window.XatIA) {{
    const script = document.createElement('script');
    script.textContent = {_json(js)};
    document.head.appendChild(script);
  }}
  window.XatIA.inicia({_json(opcions)});
  window.XatIA.api({_json(api)});
  window.XatIA.pantalla({_json(pantalla)});
}})();
</script>''', unsafe_allow_javascript=True)

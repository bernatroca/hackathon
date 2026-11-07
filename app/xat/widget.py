"""Widget persistent al document principal de Streamlit 1.67."""
import json
from pathlib import Path
from uuid import uuid4

import streamlit as st

WEB = Path(__file__).with_name('web')
PREGUNTES = {
    'Com estem avui': ['Quantes sessions són al torn equivocat?', 'Quina aula va més plena?', 'Hi cap el matí?'],
    'Horari proposat': ['On té classe aquest grup dimarts?', 'Què ha canviat respecte d’avui?', 'Per què aquesta classe s’ha mogut?'],
    'Imprevistos': ['Quines sessions afecta l’aula avariada?', 'Redacta l’avís per al grup afectat'],
}
PER_DEFECTE = ['Quina aula de 60 places està lliure dijous a les 10?', 'On té classe el grup 81 dimarts?']


@st.cache_resource(show_spinner=False)
def _api():
    # Import diferit: el backend pot no estar integrat encara. Els errors no
    # queden a la memòria cau i es pot tornar a provar al renderitzat següent.
    from xat import servidor
    url = servidor.arrenca().rstrip('/')
    return url if url.endswith('/api/xat') else url + '/api/xat'


def pantalla_actual(titol, estat):
    """Només selectors de la pàgina oberta; mai resultats ni files de dades."""
    parts = [titol]
    semestre = estat.get('semestre', 2)
    setmana = estat.get('setmana')
    linies = [f'Està mirant «{titol}».']
    if titol == 'Horari proposat':
        semestre = 2  # La graella és sempre del segon semestre.
        setmana = estat.get('p2-setmana')
        proposta = estat.get('p2-proposta', 'Avui') if estat.get('p2-vista') == 'Proposta i avui' else 'Avui'
        parts.append(str(proposta))
        linies.append(f'Compara la proposta {proposta} amb avui.' if proposta != 'Avui' else 'Mostra només l’horari d’avui.')
        grup = ' '.join(str(estat[k]) for k in ('p2-titulacio', 'p2-curs', 'p2-grup') if estat.get(k) is not None)
        if grup:
            parts.append(grup)
            linies.append(f'Estudis, curs i grup seleccionats: {grup}.')
        if estat.get('p2-aula'):
            linies.append(f'Aula seleccionada a la vista per aula: {estat["p2-aula"]}.')
    elif titol == 'Resum per a la Junta':
        semestre = 2
        proposta = estat.get('junta-proposta', 'Avui')
        parts.append(str(proposta))
        linies.append(f'Proposta seleccionada: {proposta}.')
    elif titol == 'Imprevistos':
        semestre = 2
        linies.append('Mostra els imprevistos de la proposta 5.3.')
    linies.append(f'Semestre {semestre}. Setmana: {setmana if setmana is not None else "típica"}.')
    return dict(resum=' · '.join(parts), text='\n'.join(linies),
                preguntes=PREGUNTES.get(titol, PER_DEFECTE))


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
  window.XatIA.pantalla({_json(pantalla)});
}})();
</script>''', unsafe_allow_javascript=True)

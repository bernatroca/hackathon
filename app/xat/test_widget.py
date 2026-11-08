"""Proves sense ports, amb context inventat."""
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from xat import widget


def test_arrenca_a_cada_renderitzat_i_actualitza_endpoint():
    with patch('xat.servidor.arrenca', create=True,
               side_effect=['http://localhost:8502', OSError('aturat'), 'http://localhost:8503/api/xat/']) as arrenca, \
            patch.object(widget.st, 'html') as html:
        widget.posa_widget(None)
        assert 'window.XatIA.api("http://localhost:8502/api/xat")' in html.call_args.args[0]
        widget.posa_widget(None)
        assert '%22teClau%22%3Afalse' in html.call_args.args[0]
        widget.posa_widget(None)
        assert 'window.XatIA.api("http://localhost:8503/api/xat")' in html.call_args.args[0]
        assert arrenca.call_count == 3


def test_endpoint_complet():
    with patch('xat.servidor.arrenca', create=True, return_value='http://localhost:8502/api/xat/'):
        assert widget._api() == 'http://localhost:8502/api/xat'


def test_injeccio_inline_context_segura_i_guardes():
    pantalla = dict(resum='Inventat', text='</script><script>alert(1)</script>', preguntes=['Una?'])
    with patch.object(widget, '_api', return_value='http://localhost:8502/api/xat'), patch.object(widget.st, 'html') as html:
        widget.posa_widget(pantalla)
        primer = html.call_args.args[0]
        widget.posa_widget(None)
        segon = html.call_args.args[0]
    assert primer != segon
    assert html.call_args.kwargs == {'unsafe_allow_javascript': True}
    assert "if (!window.XatIA)" in primer
    assert "getElementById('xatia-estil')" in primer
    assert 'window.XatIA.pantalla(' in primer
    assert 'window.XatIA.pantalla(null)' in segon
    assert '<script>alert(1)' not in primer
    assert '\\u003c/script\\u003e' in primer
    assert primer.count('</script>') == 1
    assert '<iframe' not in primer
    assert 'localStorage' in primer


def test_backend_absent_no_trenca_app():
    with patch.object(widget, '_api', side_effect=AttributeError('arrenca')), patch.object(widget.st, 'html') as html:
        widget.posa_widget(None)
    assert 'data:application/json,' in html.call_args.args[0]
    assert '%22teClau%22%3Afalse' in html.call_args.args[0]


def test_context_grup_i_aula_sense_arrossegar_altres_pagines():
    estat = {'semestre': 1, 'setmana': 'inventada', 'p2-proposta': '5.2',
             'p2-vista': 'Proposta i avui', 'p2-titulacio': 'GXX', 'p2-curs': '1r',
             'p2-grup': '81', 'p2-aula': 'Q9/0001', 'p2-setmana': None}
    p = widget.pantalla_actual('Horari proposat', estat)
    assert p['resum'] == 'Horari proposat · Torns nous (5.2) · GXX 1r 81'
    assert 'Q9/0001' in p['text']
    assert 'Semestre 2. Setmana: típica.' in p['text']
    p = widget.pantalla_actual('Com estem avui', estat)
    assert 'GXX' not in p['text']
    assert 'Sí, hi cap' in p['text']
    assert 'verificador oficial' in p['text']
    assert 'pic 15 de 19 aules' in p['text']
    assert p['preguntes'] == [widget.PREGUNTA_DEMO, *widget.PREGUNTES['Com estem avui'][:2]]
    estat['p2-vista'] = 'Només avui'
    assert '5.2' not in widget.pantalla_actual('Horari proposat', estat)['text']


def test_preguntes_i_junta():
    from types import SimpleNamespace
    inventades = ['Aula Q9/0001 reservada el 15/02/2027.',
                  'Assignatura inventada · TE/81 passa de 10 a 20 alumnes.']
    with patch.dict(sys.modules, {'pagines.imprevistos': SimpleNamespace(
            carrega=lambda: {'imprevistos': [{'descripcio': t} for t in inventades]})}):
        for pagina in ('Imprevistos', 'Resum per a la Junta'):
            p = widget.pantalla_actual(pagina, {'setmana': 'inventada', 'junta-proposta': '5.4'})
            assert 'Setmana:' not in p['text']
            assert 'Semestre 2.' in p['text']
            assert all(t in p['text'] for t in inventades)
        assert len(widget.pantalla_actual('Imprevistos', {})['preguntes']) == 3
        assert '5.4' in p['text']
        assert p['resum'].endswith('Amb el grau nou (5.4)')
    assert widget.pantalla_actual('Totes les respostes', {})['preguntes'] == [widget.PREGUNTA_DEMO, *widget.PREGUNTES['Totes les respostes']]
    assert widget.PREGUNTES['Resum per a la Junta'] != widget.PER_DEFECTE
    assert widget.PREGUNTES['Com estem avui'][-1] == 'Si 1r i 2n fan classe al matí, hi cabem?'
    assert widget.PREGUNTES['Horari proposat'][-1] == 'Quines classes d’aquest grup canvien de dia o hora i per què?'


def test_detall_obert_nomes_a_la_pagina_corresponent():
    from types import SimpleNamespace
    estat = {'detall_id': 'inventada', 'resultats': {
        'inventada': SimpleNamespace(titol='Una resposta inventada')}}
    for pagina in ('Com estem avui', 'Totes les respostes'):
        p = widget.pantalla_actual(pagina, estat)
        assert 'Resposta oberta: «Una resposta inventada» (identificador: inventada).' in p['text']
        assert 'Una resposta inventada' in p['resum']
        assert p['preguntes'][0] == widget.PREGUNTA_DEMO
        assert p['preguntes'][1] == 'Explica’m aquesta resposta en paraules senzilles'
    assert 'inventada' not in widget.pantalla_actual('Horari proposat', estat)['text']
    p = widget.pantalla_actual('Totes les respostes', {'detall_id': 'aforament'})
    assert 'Més alumnes que places' in p['text']


def test_imprevistos_no_disponibles_no_inventa_context():
    with patch.object(widget, '_imprevistos', side_effect=OSError('inventat')):
        p = widget.pantalla_actual('Imprevistos', {'setmana': 'inventada'})
    assert 'no està disponible' in p['text']
    assert 'Setmana:' not in p['text']
    assert 'Q1/1003' not in p['text']


def test_python_310_i_missatge_per_versions_anteriors():
    import ast

    codi = Path(widget.__file__).read_text()
    ast.parse(codi, feature_version=(3, 10))
    # El guardià s'executa abans de carregar Streamlit o el backend.
    with patch.object(sys, 'version_info', (3, 9, 6)), pytest.raises(RuntimeError, match='Python 3.10'):
        exec(compile(codi, str(widget.__file__), 'exec'), {})


def test_sense_estils_consultes_i_correccio_footer():
    css = (widget.WEB / 'xat-ia.css').read_text()
    assert '.xatia-consult' not in css
    assert 'white-space: pre-wrap' in css
    assert '.xatia footer.xatia-peu { display: block !important; }' in css


def test_consultes_js_sense_navegador():
    """Executa el JS real amb Node: SSE fragmentat, escapament i memòria."""
    import shutil
    import subprocess

    node = shutil.which('node')
    if not node:
        pytest.skip('Node no disponible per executar el JavaScript sense navegador')
    prova = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
let desat;
const sandbox = {
  window: {}, TextDecoder, AbortSignal, Event: class { constructor(type) { this.type = type; } },
  performance: { now: () => 0 },
  localStorage: {
    setItem: (k, v) => { if (k === 'prova') desat = v; },
    getItem: (k) => k === 'prova' ? desat : null,
  },
};
const source = fs.readFileSync(process.argv[1], 'utf8').replace('  window.XatIA = {', `
  window.prova = { preguntesAra, markdown, htmlMissatge, llegeixFlux, pregunta_, missatgeError, perAlServidor, desa, llegeixMemoria, estat,
    sincronitzaPlafó, sincronitzaMenu, clicManualMenu, acabaTransicio, teclaPlafó, clicFons,
    preparaInteraccio() {
      el = {fons: {}, lupa: {hidden:true},
        final: {scrollIntoView() { el.desplacaments = (el.desplacaments || 0) + 1; }},
        plafo: {contains: (node) => node === 'dins', getBoundingClientRect: () => ({width:420})}, boto: {focus() {}}};
      return el;
    },
    adreca() { return op.api; },
    prepara() { op = { clauMemoria: 'prova', preguntes: ['Pregunta per defecte'] }; },
    parcial(text) {
      el = {conversa: {innerHTML: '', setAttribute() {}}, final: {scrollIntoView() {}}};
      estat.feina = true; estat.parcial = text;
      pintaConversa();
      estat.feina = false; estat.parcial = '';
      return el.conversa.innerHTML;
    } };
  window.XatIA = {`);
vm.runInNewContext(source, sandbox);
const p = sandbox.window.prova;
p.prepara();
assert.equal(p.preguntesAra()[0], 'Pregunta per defecte');
p.estat.pantalla = {preguntes: ['Pregunta de pàgina']};
assert.equal(p.preguntesAra()[0], 'Pregunta de pàgina');
p.estat.missatges = [{role:'user', content:'Pregunta inventada'}];
assert.equal(p.preguntesAra()[0], 'Pregunta de pàgina');
p.estat.missatges.push({role:'assistant', content:'Resposta inventada'});
assert.equal(JSON.stringify(p.preguntesAra()), JSON.stringify(['Com ho saps?']));
p.estat.pantalla = {preguntes: ['Una altra pàgina']};
assert.equal(p.preguntesAra()[0], 'Com ho saps?');
p.estat.missatges = [];
assert.equal(p.preguntesAra()[0], 'Una altra pàgina');
p.estat.pantalla = null;
let mobil = false;
const classes = new Set();
const resizes = [];
const timers = new Map();
let timerId = 0;
sandbox.window.dispatchEvent = (e) => {
  assert.equal(e.type, 'resize');
  resizes.push(classes.has('xatia-obert'));
};
sandbox.window.setTimeout = (callback, ms) => {
  assert.ok(ms >= 220);
  timers.set(++timerId, callback);
  return timerId;
};
sandbox.window.clearTimeout = (id) => timers.delete(id);
sandbox.window.matchMedia = () => ({matches: mobil});
sandbox.document = {activeElement:'fora', documentElement:{classList:{toggle(nom, activa) {
  if (activa) classes.add(nom); else classes.delete(nom);
}}}};
const elements = p.preparaInteraccio();
p.estat.obert = true;
p.sincronitzaPlafó();
assert.ok(classes.has('xatia-obert'));
assert.equal(elements.fons.hidden, true);
assert.deepEqual(resizes, [true]); // Resize després d'aplicar la classe.
assert.equal(timers.size, 1);
p.sincronitzaPlafó(); // SSE/context no han de generar resizes repetits.
assert.equal(resizes.length, 1);
p.acabaTransicio({target: elements.plafo, propertyName: 'opacity'});
assert.equal(resizes.length, 1);
p.acabaTransicio({target: elements.plafo, propertyName: 'transform'});
assert.equal(resizes.length, 2);
assert.equal(timers.size, 0);
assert.ok(elements.desplacaments > 0); // Després de la transició també segueix l'última resposta.
p.clicFons();
assert.equal(p.estat.obert, true);
p.teclaPlafó({key:'Escape'});
assert.equal(p.estat.obert, true);
sandbox.document.activeElement = 'dins';
p.teclaPlafó({key:'Enter'});
assert.equal(p.estat.obert, true);
p.teclaPlafó({key:'Escape'});
assert.equal(p.estat.obert, false);
p.sincronitzaPlafó();
assert.ok(!classes.has('xatia-obert'));
assert.equal(resizes.at(-1), false);
assert.equal(timers.size, 1);
const app = {matches: (selector) => selector === '.stApp'};
p.acabaTransicio({target: app, propertyName: 'width'});
assert.equal(timers.size, 0);
const abansModes = resizes.length;
for (const mode of ['gran', 'mobil']) {
  p.estat.obert = true;
  p.estat.gran = mode === 'gran';
  mobil = mode === 'mobil';
  sandbox.document.activeElement = 'fora';
  p.sincronitzaPlafó();
  assert.ok(!classes.has('xatia-obert'));
  assert.equal(elements.fons.hidden, false);
  p.teclaPlafó({key:'Escape'});
  assert.equal(p.estat.obert, false);
  p.estat.obert = true;
  p.clicFons();
  assert.equal(p.estat.obert, false);
}
assert.equal(resizes.length, abansModes + 2);
mobil = false;
p.estat.gran = false;
p.estat.obert = true;
p.sincronitzaPlafó(); // Gran/mòbil -> petit d'ordinador.
assert.equal(resizes.at(-1), true);
assert.equal(timers.size, 1); // Les accions ràpides cancel·len el respatller antic.
const abansFinal = resizes.length;
for (const [id, callback] of timers) { timers.delete(id); callback(); }
assert.equal(resizes.length, abansFinal + 1); // També sense transitionend.
p.sincronitzaPlafó();
assert.equal(resizes.length, abansFinal + 1);
// Espai real per a menú + plafó: inclou 1440 px exactes i els canvis de mida.
let menuDesplegat = true;
let plegats = 0;
let desplegats = 0;
sandbox.window.innerWidth = 1440;
sandbox.window.innerHeight = 900;
sandbox.window.getComputedStyle = () => ({display:'block', visibility:'visible'});
const menu = {getBoundingClientRect: () => ({width:300, height:900, left:menuDesplegat ? 0 : -300,
  right:menuDesplegat ? 300 : 0, top:0, bottom:900})};
sandbox.document.querySelector = () => menu;
sandbox.document.querySelectorAll = (selector) => [{click() {
  if (selector.includes('stSidebarCollapseButton')) { menuDesplegat = false; plegats++; }
  else { menuDesplegat = true; desplegats++; }
}}];
p.estat.obert = false;
p.sincronitzaMenu();
p.estat.obert = true;
p.sincronitzaMenu();
assert.equal(plegats, 1);
assert.equal(menuDesplegat, false);
p.sincronitzaMenu();
assert.equal(plegats, 1);
p.estat.obert = false;
p.sincronitzaMenu();
assert.equal(desplegats, 1);
assert.equal(menuDesplegat, true);
sandbox.window.innerWidth = 1800;
p.estat.obert = true;
p.sincronitzaMenu();
assert.equal(menuDesplegat, true);
sandbox.window.innerWidth = 1440;
p.sincronitzaMenu();
assert.equal(menuDesplegat, false);
p.estat.obert = false;
p.sincronitzaMenu();
p.estat.obert = true;
p.sincronitzaMenu();
p.clicManualMenu({target:{closest: () => true}});
menuDesplegat = true;
p.sincronitzaMenu();
assert.equal(menuDesplegat, true); // Respecta l'acció manual mentre és obert.
p.estat.obert = false;
p.sincronitzaMenu();
menuDesplegat = false;
p.estat.obert = true;
p.sincronitzaMenu();
p.estat.obert = false;
p.sincronitzaMenu();
assert.equal(menuDesplegat, false); // No desplega un menú que ja estava plegat.
const entitats = 'inici &gt; 15.00 &lt; 20.00 &amp; &quot;hora&quot; &#39;dia&#39; &#x27;aula&#x27;';
const esperat = '<p>inici &gt; 15.00 &lt; 20.00 &amp; &quot;hora&quot; &#39;dia&#39; &#39;aula&#39;</p>';
assert.equal(p.markdown(entitats), esperat);
assert.ok(p.parcial(entitats).includes(esperat));
assert.equal(p.markdown('&lt;img src=x onerror=&quot;alert(1)&quot;&gt;'),
  '<p>&lt;img src=x onerror=&quot;alert(1)&quot;&gt;</p>');
assert.ok(!p.parcial('&lt;script&gt;alert(1)&lt;/script&gt;').includes('<script>'));
assert.equal(p.markdown('&copy; &#60; &#x3c;'), '<p>&amp;copy; &amp;#60; &amp;#x3c;</p>');
assert.equal(p.markdown('&amp;lt;'), '<p>&amp;lt;</p>');
assert.equal(p.markdown('**Hora** &gt; 15.00'), '<p><strong>Hora</strong> &gt; 15.00</p>');
const mal = '<img src=x onerror="alert(1)">';
const consultes = [{ eina: mal, args: { [mal]: mal, llarg: 'x'.repeat(120), limit: 50 },
  ok: false, consulta: 'SELECT *\nFROM inventat WHERE x < 4; ' + mal,
  id_sessio: [mal, ...Array.from({length: 10}, (_, i) => 'S' + i)], total_id: 23, error: mal }];
async function flux(fi) {
  const cru = 'data: ' + JSON.stringify({tros: 'Resposta inventada'}) + '\n\n' +
    'data: ' + JSON.stringify({consultes}) + '\n\n' + (fi ? 'data: {"fi":true}\n\n' : '');
  const bytes = new TextEncoder().encode(cru);
  let pos = 0;
  return p.llegeixFlux({getReader: () => ({read: async () => {
    if (pos >= bytes.length) return {done:true};
    const value = bytes.slice(pos, pos + 7); pos += 7;
    return {value, done:false};
  }})});
}
(async () => {
  const urls = [];
  sandbox.fetch = async (url) => { urls.push(url); return {json: async () => ({teClau: false})}; };
  await sandbox.window.XatIA.api('data:application/json,indisponible');
  assert.equal(p.estat.llesta, false);
  sandbox.fetch = async (url) => { urls.push(url); return {json: async () => ({teClau: true})}; };
  await sandbox.window.XatIA.api('http://localhost:8503/api/xat');
  assert.equal(p.adreca(), 'http://localhost:8503/api/xat');
  assert.equal(urls[1], 'http://localhost:8503/api/xat');
  assert.equal(p.estat.llesta, true);
  let acabaAntiga;
  sandbox.fetch = () => new Promise((resolve) => { acabaAntiga = resolve; });
  const antiga = sandbox.window.XatIA.api('http://localhost:8502/api/xat');
  sandbox.fetch = async () => ({json: async () => ({teClau: true})});
  await sandbox.window.XatIA.api('http://localhost:8503/api/xat');
  acabaAntiga({json: async () => ({teClau: false})});
  await antiga;
  assert.equal(p.estat.llesta, true);
  const r = await flux(true);
  assert.equal(r.text, 'Resposta inventada');
  assert.equal(r.consultes[0].total_id, 23);
  assert.equal(r.tallada, false);
  const truncada = await flux(false);
  assert.equal(truncada.tallada, false);
  assert.match(truncada.error, /connexió s’ha tallat/);
  assert.equal(truncada.consultes.length, 1);
  assert.equal(truncada.text, 'Resposta inventada');
  const cos = (events, falla = false) => {
    let llegit = false;
    return {getReader: () => ({read: async () => {
      if (llegit) { if (falla) throw new TypeError('network'); return {done:true}; }
      llegit = true;
      return {value:new TextEncoder().encode(events.map(e => 'data: ' + JSON.stringify(e) + '\n\n').join('')), done:false};
    }})};
  };
  const tall = await p.llegeixFlux(cos([{tros:'Resposta parcial'}], true));
  assert.equal(tall.text, 'Resposta parcial');
  assert.match(tall.error, /connexió s’ha tallat/);
  await assert.rejects(() => p.llegeixFlux(cos([], true)), /connexió s’ha tallat/);
  await assert.rejects(() => p.llegeixFlux(cos([])), /connexió s’ha tallat/);
  await assert.rejects(() => p.llegeixFlux(cos([{fi:true, tallada:true}])), /pregunta més concreta/);
  await assert.rejects(() => p.llegeixFlux(cos([{error:'La IA ha respost HTTP 429.'}])), /IA està saturada/);
  const errorParcial = await p.llegeixFlux(cos([{tros:'Parcial'}, {error:'La IA ha respost HTTP 429.'}]));
  assert.equal(errorParcial.text, 'Parcial');
  assert.match(errorParcial.error, /IA està saturada/);
  sandbox.fetch = async () => ({ok:false, status:429, headers:{get: () => 'application/json'}, json:async () => ({error:'HTTP 429'})});
  await assert.rejects(() => p.pregunta_([]), /IA està saturada/);
  sandbox.fetch = async () => { throw new TypeError('network'); };
  await assert.rejects(() => p.pregunta_([]), /connexió amb el servidor/);
  assert.match(p.missatgeError('HTTP 502'), /no està disponible/);
  p.estat.feina = true;
  const ambEina = await p.llegeixFlux(cos([{eina:'consulta_sql'}, {tros:'Fet'}, {fi:true}]));
  assert.equal(ambEina.text, 'Fet');
  assert.equal(p.estat.eina, 'consulta_sql');
  assert.ok(p.parcial('Encara consultant').includes('Consultant l’horari…'));
  p.estat.eina = '';
  const missatge = {role: 'assistant', content: r.text, consultes: r.consultes};
  const html = p.htmlMissatge(missatge);
  const nomesText = '<div class="xatia-missatge xatia-missatge--ia"><p>Resposta inventada</p></div>';
  assert.equal(html, nomesText); // Sense bloc, SQL, arguments, sessions ni errors de consultes.
  assert.equal(p.htmlMissatge({role:'assistant', content:r.text}), nomesText);
  p.estat.missatges = [missatge];
  p.desa();
  p.estat.missatges = [];
  p.llegeixMemoria();
  assert.equal(p.estat.missatges[0].consultes[0].total_id, 23);
  assert.deepEqual(JSON.parse(JSON.stringify(p.estat.missatges[0].consultes)), consultes);
  assert.equal(p.htmlMissatge(p.estat.missatges[0]), nomesText); // Tampoc en converses desades.
  const enviat = JSON.parse(JSON.stringify(p.perAlServidor()));
  assert.deepEqual(enviat, [{role:'assistant', content:'Resposta inventada'}]);
})().catch((error) => { console.error(error); process.exitCode = 1; });
'''
    resultat = subprocess.run([node, '-e', prova, str(widget.WEB / 'xat-ia.js')],
                              text=True, capture_output=True, timeout=15)
    assert resultat.returncode == 0, resultat.stderr


def test_css_plafó_acoblat_i_compactacio():
    css = (widget.WEB / 'xat-ia.css').read_text()
    assert 'html.xatia-obert .stApp' in css
    assert 'width: calc(100% - var(--xatia-amplada)) !important' in css
    assert 'transform: translateZ(0)' in css
    assert 'html.xatia-obert [data-testid="stAppViewContainer"]' in css
    assert 'html.xatia-obert [data-testid="stMain"]' in css
    assert 'margin-right: var(--xatia-amplada)' not in css
    assert 'html.xatia-obert [data-testid="stMainBlockContainer"]' in css
    assert 'max-width: min(1240px, 100%) !important' in css
    assert 'html.xatia-obert [data-testid="stHeader"]' in css
    assert 'html.xatia-obert .st-key-p2-pagina .st-key-p2-guia' in css
    assert 'html.xatia-obert .st-key-p2-pagina .st-key-p2-obre-guia' in css
    assert 'max-width: calc(100vw - var(--xatia-amplada) - 36px) !important' in css
    assert 'overflow-x: clip' in css
    assert 'stSidebar' not in css
    assert '.xatia:not(.xatia--gran) .xatia-fons { pointer-events: none; }' in css
    assert '(min-width: 700px) and (max-width: 1099px)' in css
    assert 'flex-wrap: wrap' in css
    assert '[data-testid="stColumn"]' in css
    assert 'transition: width 0.22s ease' in css
    assert 'prefers-reduced-motion' in css


def test_accessibilitat_i_etiqueta_context():
    js = (widget.WEB / 'xat-ia.js').read_text()
    assert 'role="log" aria-live="polite"' in js
    assert "setAttribute('aria-busy', String(estat.feina))" in js
    assert 'aria-controls="xatia-plafo"' in js
    assert "setAttribute('aria-expanded', String(obert))" in js
    assert '`Context: ${veu}`' in js


@pytest.mark.parametrize('pagina', [*widget.PREGUNTES, 'Pàgina inventada'])
def test_demo_primera_a_totes_les_pagines(pagina):
    with patch.object(widget, '_imprevistos', return_value=[]):
        preguntes = widget.pantalla_actual(pagina, {})['preguntes']
    assert preguntes[0] == 'Quantes aules queden lliures dimarts a les 10?'
    assert len(preguntes) <= 3
    assert len(preguntes) == len(set(preguntes))
    assert widget.PER_DEFECTE[0] == preguntes[0]


def test_benvinguda_planera():
    with patch.object(widget, '_api', return_value='/api/xat'), patch.object(widget.st, 'html') as html:
        widget.posa_widget(None)
    assert 'Pregunta’m per aules, grups o l’horari proposat. Respondré amb les dades.' in html.call_args.args[0]

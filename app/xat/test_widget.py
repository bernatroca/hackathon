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
    assert p['resum'] == 'Horari proposat · 5.2 · GXX 1r 81'
    assert 'Q9/0001' in p['text']
    assert 'Semestre 2. Setmana: típica.' in p['text']
    p = widget.pantalla_actual('Com estem avui', estat)
    assert 'GXX' not in p['text']
    assert '5.2' not in p['text']
    assert p['preguntes'][0] == 'Quantes sessions són al torn equivocat?'
    estat['p2-vista'] = 'Només avui'
    assert '5.2' not in widget.pantalla_actual('Horari proposat', estat)['text']


def test_preguntes_i_junta():
    assert len(widget.pantalla_actual('Imprevistos', {})['preguntes']) == 2
    assert widget.pantalla_actual('Totes les respostes', {})['preguntes'] == widget.PER_DEFECTE
    assert '5.4' in widget.pantalla_actual('Resum per a la Junta', {'junta-proposta': '5.4'})['text']


def test_estils_consultes_i_correccio_footer():
    css = (widget.WEB / 'xat-ia.css').read_text()
    assert '.xatia-consultes summary' in css
    assert '.xatia-consulta pre' in css
    assert 'overflow-wrap: anywhere' in css
    assert 'focus-visible' in css
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
  window.prova = { htmlConsultes, copiaIds, descriuArgument, markdown, htmlMissatge, llegeixFlux, perAlServidor, desa, llegeixMemoria, estat,
    sincronitzaPlafó, acabaTransicio, teclaPlafó, clicFons,
    preparaInteraccio() {
      el = {fons: {}, lupa: {hidden:true},
        plafo: {contains: (node) => node === 'dins'}, boto: {focus() {}}};
      return el;
    },
    adreca() { return op.api; },
    prepara() { op = { clauMemoria: 'prova' }; },
    parcial(text) {
      el = {conversa: {innerHTML: ''}, final: {scrollIntoView() {}}};
      estat.feina = true; estat.parcial = text;
      pintaConversa();
      estat.feina = false; estat.parcial = '';
      return el.conversa.innerHTML;
    } };
  window.XatIA = {`);
vm.runInNewContext(source, sandbox);
const p = sandbox.window.prova;
p.prepara();
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
  assert.equal(truncada.tallada, true);
  assert.equal(truncada.consultes.length, 1);
  const missatge = {role: 'assistant', content: r.text, consultes: r.consultes};
  const html = p.htmlMissatge(missatge);
  const nomesText = '<div class="xatia-missatge xatia-missatge--ia"><p>Resposta inventada</p></div>';
  assert.equal(html, nomesText); // Sense bloc, SQL, arguments, sessions ni errors de consultes.
  assert.equal(p.htmlMissatge({role:'assistant', content:r.text}), nomesText);
  const bones = [{eina:'aules_lliures', ok:true,
    args:{dia:'J', hora_ini:'10:00', durada_min:60, places_min:60, proposta:'avui'},
    id_sessio:Array.from({length:12}, (_, i) => 'S900' + i), total_id:23,
    consulta:'SELECT * FROM inventat WHERE x < 4; ' + mal},
    {eina:'ocupacio_aula', ok:true, args:{aula:'Q9/0001'}, id_sessio:[], consulta:'cap resultat'},
    ...consultes];
  const ambConsultes = {...missatge, consultes:bones};
  const comprovacio = p.htmlMissatge(ambConsultes);
  assert.ok(comprovacio.includes('<details class="xatia-consultes"><summary>Comprova-ho</summary>'));
  assert.ok(!comprovacio.includes('<details open'));
  assert.equal((comprovacio.match(/class="xatia-consulta"/g) || []).length, 2);
  for (const text of ['Aules lliures', 'dia: dijous', 'hora: 10:00', 'durada: 60 min',
    '60 places o més', 'horari d’avui', '+13 més', 'Copia', 'cap resultat',
    'Ocupació de l’aula', 'Q9/0001', 'x &lt; 4', '&lt;img']) assert.ok(comprovacio.includes(text), text);
  assert.ok(!comprovacio.includes('<img'));
  assert.ok(!comprovacio.includes('S90010'));
  assert.ok(!comprovacio.includes('S90011'));
  assert.ok(!p.htmlMissatge({role:'user', content:'Hola', consultes:bones}).includes('Comprova-ho'));
  assert.equal(p.htmlConsultes([]), '');
  assert.equal(p.htmlConsultes(null), '');
  assert.equal(p.htmlConsultes([{ok:false}]), '');
  for (const eina of ['horari_grup','xifra','resultat_proposta','consulta_sql','prova_canvi']) {
    const h = p.htmlConsultes([{ok:true,eina,args:{apartat:'5.2',canvi:{tipus:'moure',id_sessio:'S90001'}}}]);
    assert.ok(h.includes('horari proposat: 5.2'));
    assert.ok(h.includes('canvi: tipus: moure una classe · sessió: S90001'));
    assert.ok(!h.includes(eina));
  }
  assert.equal(p.descriuArgument('proposta', '5.2'), 'horari proposat: 5.2');
  const status = {textContent:''};
  const codeIds = {};
  const boto = {dataset:{ids:'S90001,S90002'}, parentElement:{querySelector:(selector) => selector === 'code' ? codeIds : status}};
  let copiat;
  sandbox.navigator = {clipboard:{writeText:async (text) => {copiat = text;}}};
  await p.copiaIds(boto);
  assert.equal(copiat, 'S90001,S90002');
  assert.equal(status.textContent, 'Copiat');
  let temporal, eliminats = 0, seleccionats = 0, focusRestaurat = 0;
  sandbox.document.activeElement = {focus:() => {focusRestaurat++;}};
  sandbox.document.createElement = (tag) => {
    assert.equal(tag, 'textarea');
    temporal = {style:{}, setAttribute:(k,v) => {assert.equal(k,'readonly');},
      select:() => {seleccionats++;}, remove:() => {eliminats++;}};
    return temporal;
  };
  sandbox.document.body = {appendChild:(element) => {assert.equal(element,temporal);}};
  sandbox.document.execCommand = (command) => {
    assert.equal(command, 'copy');
    assert.equal(temporal.value, 'S90001,S90002');
    return true;
  };
  sandbox.navigator.clipboard.writeText = async () => {throw new Error('denegat');};
  await p.copiaIds(boto);
  assert.equal(status.textContent, 'Copiat');
  delete sandbox.navigator.clipboard;
  await p.copiaIds(boto);
  assert.equal(status.textContent, 'Copiat');
  assert.equal(eliminats, 2);
  assert.equal(seleccionats, 2);
  assert.equal(focusRestaurat, 2);
  let contingut, rangAfegit, netejat = false;
  const rang = {selectNodeContents:(node) => {contingut = node;}};
  sandbox.document.createRange = () => rang;
  sandbox.window.getSelection = () => ({removeAllRanges:() => {netejat = true;},
    addRange:(r) => {rangAfegit = r;}});
  for (const falla of [() => false, () => {throw new Error('bloquejat');}]) {
    sandbox.document.execCommand = falla;
    await p.copiaIds(boto);
    assert.equal(status.textContent, 'Seleccionat: prem Cmd+C o Ctrl+C per copiar-ho');
    assert.equal(contingut, codeIds);
    assert.equal(rangAfegit, rang);
    assert.ok(netejat);
  }
  assert.equal(eliminats, 4);
  p.estat.missatges = [ambConsultes];
  p.desa();
  p.estat.missatges = [];
  p.llegeixMemoria();
  assert.equal(p.estat.missatges[0].consultes[0].total_id, 23);
  assert.deepEqual(JSON.parse(JSON.stringify(p.estat.missatges[0].consultes)), bones);
  assert.equal(p.htmlMissatge(p.estat.missatges[0]), comprovacio); // També en converses desades.
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

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
    assert '.xatia-consultes' in css
    assert 'white-space: pre-wrap' in css
    assert '.xatia-consulta-error { color: var(--xatia-error); }' in css
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
  window: {}, TextDecoder, AbortSignal, performance: { now: () => 0 },
  localStorage: {
    setItem: (k, v) => { if (k === 'prova') desat = v; },
    getItem: (k) => k === 'prova' ? desat : null,
  },
};
const source = fs.readFileSync(process.argv[1], 'utf8').replace('  window.XatIA = {', `
  window.prova = { markdown, htmlMissatge, llegeixFlux, perAlServidor, desa, llegeixMemoria, estat,
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
  assert.ok(html.includes('<details class="xatia-consultes" open>'));
  assert.ok(html.includes('Com es comprova · 1 consulta'));
  assert.ok(html.includes('i 13 més'));
  assert.ok(html.includes('SELECT *\nFROM inventat WHERE x &lt; 4;'));
  assert.ok(html.includes('xatia-consulta-error'));
  assert.ok(html.includes('&lt;img src=x onerror=&quot;alert(1)&quot;&gt;'));
  assert.ok(!html.includes('<img'));
  assert.ok(!html.includes('<code>S9</code>'));
  assert.ok(!html.includes('x'.repeat(120)));
  assert.ok(!p.htmlMissatge({role:'assistant', content:'Antiga'}).includes('<details'));
  const sql = 'SELECT * FROM inventat';
  const original = {eina:'consulta_sql', args:{sql, proposta:'avui', filtre:{b:2, a:1}}, consulta:sql};
  const duplicada = {eina:'consulta_sql', args:{filtre:{a:1, b:2}, proposta:'avui', sql}, consulta:sql};
  const render = (consultes) => p.htmlMissatge({role:'assistant', content:'Prova', consultes});
  const unica = render([original, duplicada]);
  assert.ok(unica.includes('Com es comprova · 1 consulta</summary>'));
  assert.equal((unica.match(/class="xatia-consulta"/g) || []).length, 1);
  assert.equal(unica.split(sql).length - 1, 1);
  assert.ok(!unica.includes('sql='));
  assert.ok(unica.includes('proposta=avui'));
  assert.ok(render([{...original, consulta:''}]).includes('sql='));
  // Només es deduplica quan coincideixen tots tres camps, sense escurçar-los.
  for (const diferent of [
    {...original, eina:'altra_eina'},
    {...original, args:{...original.args, proposta:'5.2'}},
    {...original, consulta:sql + ' LIMIT 1'},
  ]) {
    assert.ok(render([original, duplicada, diferent]).includes('Com es comprova · 2 consultes</summary>'));
  }
  p.estat.missatges = [missatge];
  p.desa();
  p.estat.missatges = [];
  p.llegeixMemoria();
  assert.equal(p.estat.missatges[0].consultes[0].total_id, 23);
  const enviat = JSON.parse(JSON.stringify(p.perAlServidor()));
  assert.deepEqual(enviat, [{role:'assistant', content:'Resposta inventada'}]);
})().catch((error) => { console.error(error); process.exitCode = 1; });
'''
    resultat = subprocess.run([node, '-e', prova, str(widget.WEB / 'xat-ia.js')],
                              text=True, capture_output=True, timeout=15)
    assert resultat.returncode == 0, resultat.stderr

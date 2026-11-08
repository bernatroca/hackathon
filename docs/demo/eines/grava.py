"""Gravació contínua de l'app amb Chromium sense finestra (CDP Page.startScreencast).

Cada fotograma que pinta el navegador es desa amb la seva hora. Després, `munta()` en fa un vídeo
a 30 fps constants, i pot escurçar trams d'espera (per exemple, mentre la IA pensa) sense tallar.
El cursor i els rètols són elements que s'afegeixen a la pàgina, i per això surten a la gravació.
"""
import asyncio, base64, bisect, json, os, subprocess, time, itertools
import requests, websockets

CHROME = os.path.expanduser('~/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/'
                            'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing')
PORT = 9334

CAPA = r"""
(() => {
  if (window.__demo && document.getElementById('demo-cursor')) return;
  const css = document.createElement('style');
  css.textContent = `
    #demo-cursor{position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;pointer-events:none;
      filter:drop-shadow(0 2px 3px rgba(0,0,0,.35));transition:opacity .3s}
    #demo-ona{position:fixed;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;border:3px solid #2b78e4;
      z-index:2147483646;pointer-events:none;opacity:0}
    #demo-ona.va{animation:demo-ona .45s ease-out}
    @keyframes demo-ona{from{opacity:1;transform:scale(1)}to{opacity:0;transform:scale(3.2)}}
    #demo-rotol{position:fixed;left:50%;bottom:30px;transform:translate(-50%,16px);z-index:2147483647;pointer-events:none;
      padding:13px 24px 15px;border-radius:14px;background:rgba(20,22,28,.92);color:#fff;font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;
      box-shadow:0 14px 40px rgba(0,0,0,.28);opacity:0;transition:opacity .4s,transform .4s;max-width:1180px;width:max-content}
    #demo-rotol.ve{opacity:1;transform:translate(-50%,0)}
    #demo-rotol .part{font:700 14px/1.2 -apple-system,sans-serif;letter-spacing:.11em;text-transform:uppercase;color:#9cc3ff}
    #demo-rotol .titol{font:800 29px/1.18 -apple-system,"Helvetica Neue",sans-serif;letter-spacing:-.01em;margin-top:5px}
    #demo-rotol .detall{font:500 19px/1.32 -apple-system,sans-serif;color:#d6dae2;margin-top:5px}
    #demo-part{position:fixed;top:14px;right:18px;z-index:2147483647;pointer-events:none;padding:8px 15px;border-radius:999px;
      background:rgba(20,22,28,.88);color:#fff;font:700 14px -apple-system,sans-serif;letter-spacing:.04em;opacity:0;transition:opacity .4s}
    #demo-part.ve{opacity:1}
    #demo-part b{color:#9cc3ff}
    #demo-negre{position:fixed;inset:0;z-index:2147483647;background:#0e0f12;color:#fff;display:grid;place-content:center;text-align:center;
      opacity:0;transition:opacity .6s;pointer-events:none;font:800 64px/1.1 -apple-system,"Helvetica Neue",Arial,sans-serif}
    #demo-negre small{display:block;margin-top:18px;font:600 26px -apple-system,sans-serif;color:#9cc3ff;letter-spacing:.12em;text-transform:uppercase}
    #demo-negre.ve{opacity:1}
    #demo-terminal{position:fixed;inset:0;z-index:2147483646;background:#1b1d22;color:#d7dbe2;opacity:0;transition:opacity .4s;
      pointer-events:none;display:flex;flex-direction:column}
    #demo-terminal.ve{opacity:1}
    #demo-terminal .barra{height:34px;flex:none;background:#2a2d34;display:flex;align-items:center;gap:8px;padding:0 14px;
      font:13px -apple-system,sans-serif;color:#9aa1ad}
    #demo-terminal .barra i{width:12px;height:12px;border-radius:50%;background:#ff5f57;display:inline-block}
    #demo-terminal .barra i:nth-child(2){background:#febc2e}#demo-terminal .barra i:nth-child(3){background:#28c840}
    #demo-terminal .barra span{flex:1;text-align:center;margin-right:60px}
    #demo-terminal pre{margin:0;padding:18px 24px 170px;flex:1;overflow:hidden;white-space:pre;font:17.5px/1.36 "SF Mono",Menlo,monospace}
    body.demo-term .demo-amagat{visibility:hidden!important}
    #demo-terminal .ordre{color:#fff}#demo-terminal .prompt{color:#8fe0a6}
    #demo-terminal .linia-ordre{white-space:pre-wrap;word-break:break-all}
    #demo-terminal.ajusta pre div{white-space:pre-wrap}
    #demo-terminal .valida{color:#8fe0a6;font-weight:700}#demo-terminal .novalida{color:#ff8f86;font-weight:700}
    #demo-terminal .cursor{display:inline-block;width:.6em;background:#d7dbe2;animation:demo-parpelleja 1s steps(1) infinite}
    @keyframes demo-parpelleja{50%{opacity:0}}`;
  document.head.appendChild(css);
  const c = document.createElement('div');
  c.id = 'demo-cursor';
  c.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M3 2l7.5 19 2.6-7.9L21 10.5z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  const o = document.createElement('div'); o.id = 'demo-ona';
  const r = document.createElement('div'); r.id = 'demo-rotol';
  const n = document.createElement('div'); n.id = 'demo-negre';
  const tm = document.createElement('div'); tm.id = 'demo-terminal';
  const pt = document.createElement('div'); pt.id = 'demo-part';
  tm.innerHTML = '<div class="barra"><i></i><i></i><i></i><span>repte-horaris-escola — zsh</span></div><pre></pre>';
  document.body.append(o, r, n, tm, pt, c);
  const pre = tm.querySelector('pre');
  const esc = (t) => String(t).replace(/[&<>]/g, (ch) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[ch]));
  const pos = window.__demoPos || [1500, 700];
  window.__demo = {
    mou(x, y) { window.__demoPos = [x, y]; c.style.transform = `translate(${x - 4}px, ${y - 2}px)`; },
    clic(x, y) { o.style.left = x + 'px'; o.style.top = y + 'px'; o.classList.remove('va'); void o.offsetWidth; o.classList.add('va'); },
    rotol(t) { if (!t) { r.classList.remove('ve'); return; }
      if (typeof t === 'string') t = {titol: t};
      r.innerHTML = (t.part ? `<div class="part">${esc(t.part)}</div>` : '') + `<div class="titol">${esc(t.titol)}</div>`
        + (t.detall ? `<div class="detall">${esc(t.detall)}</div>` : '');
      r.classList.add('ve'); },
    part(t) { if (!t) { pt.classList.remove('ve'); return; } pt.innerHTML = t; pt.classList.add('ve'); },
    negre(t, s) { n.innerHTML = t ? `${t}<small>${s || ''}</small>` : ''; n.classList.toggle('ve', !!t); },
    amaga(v) { c.style.opacity = v ? 0 : 1; },
    terminal(v) { tm.classList.toggle('ve', !!v); document.body.classList.toggle('demo-term', !!v);
      // els botons flotants de l'app (guia) no han de sortir per sobre del terminal
      [...document.querySelectorAll('a, button')].filter(e => /Com funciona\?/.test(e.innerText || ''))
        .forEach(e => { let f = e; while (f && f !== document.body && getComputedStyle(f).position !== 'fixed') f = f.parentElement;
          (f && f !== document.body ? f : e).classList.add('demo-amagat'); }); },
    puja(ms) { const ps = [...pre.querySelectorAll('.prompt')]; const d = ps.at(-1).parentElement;
      const y0 = pre.scrollTop, y1 = Math.max(d.offsetTop - pre.offsetTop - 10, 0), t0 = performance.now();
      const suau = (u) => u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
      return new Promise((ok) => { const pas = (t) => { const u = Math.min((t - t0) / ms, 1);
        pre.scrollTop = y0 + (y1 - y0) * suau(u); if (u < 1) requestAnimationFrame(pas); else ok(); }; requestAnimationFrame(pas); }); },
    netejaTerminal(nom, ajusta) { pre.innerHTML = ''; tm.querySelector('.barra span').textContent = nom + ' — zsh';
      tm.classList.toggle('ajusta', !!ajusta); },
    prompt(nom) { pre.querySelector('.cursor')?.remove();
      pre.insertAdjacentHTML('beforeend', `<div class="linia-ordre"><span class="prompt">${esc(nom || 'repte-horaris-escola')} %</span> <span class="ordre"></span><span class="cursor">&nbsp;</span></div>`);
      pre.scrollTop = pre.scrollHeight; },
    tecleja(t) { const o = [...pre.querySelectorAll('.ordre')].at(-1); o.textContent += t; },
    linia(t) { pre.querySelector('.cursor')?.remove();
      const cls = /^Veredicte: NO VALIDA/.test(t) ? 'novalida' : /^Veredicte: VALIDA/.test(t) ? 'valida' : '';
      pre.insertAdjacentHTML('beforeend', `<div class="${cls}">${esc(t) || '&nbsp;'}</div>`); pre.scrollTop = pre.scrollHeight; },
    desplaca(dy, ms) {
      const el = document.querySelector('[data-testid=stMain]') || document.scrollingElement;
      const y0 = el.scrollTop, t0 = performance.now();
      const suau = (u) => u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
      return new Promise((ok) => { const pas = (t) => { const u = Math.min((t - t0) / ms, 1);
        el.scrollTop = y0 + dy * suau(u); if (u < 1) requestAnimationFrame(pas); else ok(el.scrollTop); }; requestAnimationFrame(pas); });
    },
  };
  window.__demo.mou(...pos);
})()
"""


def obre_chrome(perfil, css_w, css_h, escala):
    # La pàgina fa css_w×css_h píxels CSS i el screencast, css×escala píxels reals.
    # En mode sense finestra, la finestra perd 143 px CSS d'alçada: per això se'ls sumem.
    p = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={perfil}',
                          f'--window-size={css_w},{css_h + 143}', f'--force-device-scale-factor={escala:.7f}',
                          '--hide-scrollbars', '--force-color-profile=srgb',
                          '--lang=ca', '--disable-gpu-vsync', 'about:blank'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            requests.get(f'http://127.0.0.1:{PORT}/json/version', timeout=1); break
        except Exception:
            time.sleep(0.2)
    return p


class Pestanya:
    """Connexió CDP amb un lector en segon pla: respostes i fotogrames del screencast."""

    def __init__(self, ws, carpeta):
        self.ws, self.ids, self.pendents = ws, itertools.count(1), {}
        self.carpeta, self.fotogrames, self.gravant = carpeta, [], False
        self.lector = asyncio.create_task(self._llegeix())
        self.marques = []  # (inici, fi, durada_nova): trams que s'escurcen al muntatge
        self.capitols = []  # (nom, hora): per saber on comença cada tram al vídeo
        self.registre_rotols = []  # (hora, tipus, valor): quan entra o surt cada rètol i etiqueta

    @classmethod
    async def obre(cls, carpeta, css_w, css_h, escala):
        t = [x for x in requests.get(f'http://127.0.0.1:{PORT}/json').json() if x['type'] == 'page'][0]
        ws = await websockets.connect(t['webSocketDebuggerUrl'], max_size=2 ** 28)
        p = cls(ws, carpeta)
        await p.cmd('Page.enable'); await p.cmd('Runtime.enable')
        await p.cmd('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'light'}])
        p.mida = (round(css_w * escala), round(css_h * escala))
        return p

    async def _llegeix(self):
        async for brut in self.ws:
            m = json.loads(brut)
            if 'id' in m and m['id'] in self.pendents:
                self.pendents.pop(m['id']).set_result(m)
            elif m.get('method') == 'Page.screencastFrame':
                q = m['params']
                if self.gravant:
                    n = len(self.fotogrames)
                    cami = os.path.join(self.carpeta, f'f{n:05d}.jpg')
                    with open(cami, 'wb') as f:
                        f.write(base64.b64decode(q['data']))
                    self.fotogrames.append((q['metadata']['timestamp'], cami))
                asyncio.create_task(self.cmd('Page.screencastFrameAck', sessionId=q['sessionId']))

    async def cmd(self, metode, **params):
        i = next(self.ids)
        fut = asyncio.get_event_loop().create_future()
        self.pendents[i] = fut
        await self.ws.send(json.dumps({'id': i, 'method': metode, 'params': params}))
        m = await fut
        if 'error' in m:
            raise RuntimeError(f'{metode}: {m["error"]}')
        return m.get('result', {})

    async def js(self, expr):
        r = await self.cmd('Runtime.evaluate', expression=expr, awaitPromise=True, returnByValue=True)
        if 'exceptionDetails' in r:
            raise RuntimeError(r['exceptionDetails'])
        return r['result'].get('value')

    async def capa(self):
        await self.js(CAPA)

    async def comenca(self):
        self.gravant = True
        await self.cmd('Page.startScreencast', format='jpeg', quality=92, maxWidth=self.mida[0], maxHeight=self.mida[1], everyNthFrame=1)

    async def para(self):
        await self.cmd('Page.stopScreencast')
        self.gravant = False

    # --- accions visibles ---
    async def espera_text(self, text, limit=60):
        t0 = time.time()
        while time.time() - t0 < limit:
            if await self.js(f'document.body && document.body.innerText.includes({json.dumps(text)})'):
                return
            await asyncio.sleep(0.2)
        raise TimeoutError(text)

    async def quiet(self, limit=60):
        """Espera que Streamlit acabi de recalcular."""
        t0 = time.time(); await asyncio.sleep(0.4)
        while time.time() - t0 < limit:
            if not await self.js("!!document.querySelector('[data-testid=stStatusWidget], [data-testid=stSpinner], [data-testid=stSkeleton]')"):
                return
            await asyncio.sleep(0.15)

    async def on(self, selector, quin=0, text=None):
        filtre = f'.filter(e => e.innerText && e.innerText.trim().startsWith({json.dumps(text)}))' if text else ''
        r = await self.js(f"""(() => {{ const els = [...document.querySelectorAll({json.dumps(selector)})]{filtre}.filter(e => e.getClientRects().length);
            const e = els.at({quin}); if (!e) return null; const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2, r.y, r.height]; }})()""")
        if not r:
            raise RuntimeError(f'no trobo {selector} {text or ""}')
        return r

    async def mou(self, x, y, segons=0.9):
        await self.capa()
        x0, y0 = await self.js('window.__demoPos || [1500, 700]')
        t0 = time.time()
        while True:  # segueix el rellotge: dura `segons` encara que el navegador vagi lent
            u = min((time.time() - t0) / segons, 1.0)
            v = 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
            x1, y1 = x0 + (x - x0) * v, y0 + (y - y0) * v
            await self.js(f'window.__demo.mou({x1:.1f}, {y1:.1f})')
            await self.cmd('Input.dispatchMouseEvent', type='mouseMoved', x=x1, y=y1)
            if u >= 1:
                break
            await asyncio.sleep(0.012)

    async def clica(self, x, y, segons=0.9):
        await self.mou(x, y, segons)
        await asyncio.sleep(0.12)
        await self.js(f'window.__demo.clic({x:.1f}, {y:.1f})')
        for tipus in ('mousePressed', 'mouseReleased'):
            await self.cmd('Input.dispatchMouseEvent', type=tipus, x=x, y=y, button='left', clickCount=1)

    async def clica_on(self, selector, quin=0, text=None, segons=0.9):
        x, y, *_ = await self.on(selector, quin, text)
        await self.clica(x, y, segons)

    async def escriu(self, text, ritme=0.055):
        t0, fet = time.time(), 0
        while fet < len(text):  # lletres segons el rellotge, no segons la velocitat del navegador
            toca = min(len(text), int((time.time() - t0) / ritme) + 1)
            if toca > fet:
                await self.cmd('Input.insertText', text=text[fet:toca]); fet = toca
            await asyncio.sleep(0.01)

    async def tecla(self, nom, codi):
        await self.cmd('Input.dispatchKeyEvent', type='keyDown', key=nom, code=nom, windowsVirtualKeyCode=codi, text='\r' if codi == 13 else '')
        await self.cmd('Input.dispatchKeyEvent', type='keyUp', key=nom, code=nom, windowsVirtualKeyCode=codi)

    async def desplaca(self, dy, segons=1.2):
        await self.capa()
        await self.js(f'window.__demo.desplaca({dy}, {int(segons * 1000)})')

    async def rotol(self, text, part=None, detall=None):
        """Rètol de baix: la part del repte (petit), què es veu (gran) i què hi tenim en compte."""
        await self.capa()
        valor = {'titol': text, 'part': part, 'detall': detall} if text else ''
        self.registre_rotols.append((time.time(), 'rotol', valor))
        await self.js(f'window.__demo.rotol({json.dumps(valor)})')

    async def part(self, html):
        """Etiqueta fixa a dalt a la dreta amb la part del repte que es resol."""
        await self.capa()
        self.registre_rotols.append((time.time(), 'part', html))
        await self.js(f'window.__demo.part({json.dumps(html)})')


def munta(fotogrames, marques, sortida, fps=30, crf=20, final_negre=0.0):
    """Fa el vídeo a fps constants. `marques`: trams (inici, fi, durada_nova) que s'escurcen."""
    ts = [t for t, _ in fotogrames]
    inici, fi = ts[0], ts[-1] + final_negre
    marques = sorted(marques)

    def font(t_sortida):
        """Temps de la gravació que correspon a un temps del vídeo."""
        t, src = 0.0, inici
        for a, b, d in marques:
            if t + (a - src) >= t_sortida:
                return src + (t_sortida - t)
            t += a - src
            if t + d >= t_sortida:
                return a + (t_sortida - t) * (b - a) / d
            t += d; src = b
        return src + (t_sortida - t)

    durada = (fi - inici) - sum((b - a) - d for a, b, d in marques)
    n = int(durada * fps)
    ff = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps),
                           '-c:v', 'mjpeg', '-i', '-', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf),
                           '-pix_fmt', 'yuv420p', '-r', str(fps), '-movflags', '+faststart', sortida], stdin=subprocess.PIPE)
    darrer = None
    for k in range(n):
        s = font(k / fps)
        i = max(bisect.bisect_right(ts, s) - 1, 0)
        if i != darrer:
            dades = open(fotogrames[i][1], 'rb').read(); darrer = i
        ff.stdin.write(dades)
    ff.stdin.close(); ff.wait()
    return n / fps

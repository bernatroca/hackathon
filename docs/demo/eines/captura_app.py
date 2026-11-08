"""Captures de l'app real per al vídeo «Com funciona l'app» (docs/demo/demo-app.mp4).

Cal l'app engegada al port 8511 (launch.json, configuració «demo») amb la IA real.
Ús (des de l'arrel del repositori):
  DPR=2 python docs/demo/eines/captura_app.py docs/demo/muntatge-app/img-png
"""
import asyncio, html, os, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import launch, Tab, mouse_click, center

B = 'http://localhost:8511/'
O = sys.argv[1].rstrip('/') + '/'
NOMES = sys.argv[2:]  # p. ex. «p2» per refer només l'horari proposat i l'assistent
ARREL = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
REPTE = os.environ.get('REPTE_DIR', '/Users/bernatroca/Bernat/Hackathon/repte/repte-horaris-escola')
PREGUNTA = 'On té classe el grup 21 de 3r de Química dijous, a la proposta 5.2? Digues-me quines sessions són.'
MAIN = "document.querySelector('[data-testid=stMain]')"


async def carrega(t, ruta, text):
    await t.goto(B + ruta); await t.wait_text(text); await t.idle(); await asyncio.sleep(2.5); await t.idle()


async def al_centre(t, text, bloc='center', quin='pop()'):
    await t.js(f"[...document.querySelectorAll('p, h1, h2, h3, h4, span, summary, div')].filter(e => e.children.length < 3 && e.innerText && e.innerText.trim().startsWith({text!r})).{quin}.scrollIntoView({{block: {bloc!r}}})")
    await asyncio.sleep(1)


async def tria(t, clau, text):
    x, y = await center(t, f'.st-key-{clau} input'); await mouse_click(t, x, y); await asyncio.sleep(0.6)
    await t.cmd('Input.insertText', text=text); await asyncio.sleep(0.8)
    x, y = await center(t, '[role=option]'); await mouse_click(t, x, y)
    await t.idle(); await asyncio.sleep(2)


def terminal_html(cami):
    """Sortida real del verificador oficial per al 5.2, en una pàgina amb aspecte de terminal."""
    p = os.path.join(ARREL, 'resultats', 'nivell2', '5.2')
    ordre = ['python3', '-m', 'horaris', 'check', os.path.join(p, 'proposta.csv'), '--semestre', '2',
             '--relaxacions', os.path.join(p, 'relaxacions.csv')]
    t0 = time.time()
    sortida = subprocess.run(ordre, cwd=REPTE, capture_output=True, text=True).stdout
    segons = time.time() - t0
    linies = sortida.splitlines()[:28]
    cos = []
    for l in linies:
        e = html.escape(l)
        if l.startswith('Veredicte'):
            e = f'<b class="v">{e}</b>'
        elif '[REL]' in l:
            e = f'<span class="rel">{e}</span>'
        elif '[OK ]' in l:
            e = e.replace('[OK ]', '<span class="ok">[OK ]</span>')
        cos.append(e)
    mostra = 'python -m horaris check resultats/nivell2/5.2/proposta.csv --semestre 2 \\\n    --relaxacions resultats/nivell2/5.2/relaxacions.csv'
    open(cami, 'w').write(f'''<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#1b1d22;color:#d7dbe2;font:17px/1.42 "SF Mono",Menlo,monospace}}
.barra{{height:38px;background:#2a2d34;display:flex;align-items:center;gap:8px;padding:0 16px}}
.barra i{{width:13px;height:13px;border-radius:50%;background:#ff5f57;display:inline-block}}
.barra i:nth-child(2){{background:#febc2e}}.barra i:nth-child(3){{background:#28c840}}
.barra span{{margin-left:12px;color:#9aa1ad;font:14px -apple-system,sans-serif}}
pre{{margin:0;padding:22px 30px;white-space:pre;font:inherit}}
.ordre{{color:#9cc3ff}}.v{{color:#8fe0a6}}.ok{{color:#8fe0a6}}.rel{{color:#f5c26b}}.temps{{color:#9aa1ad}}
</style><div class="barra"><i></i><i></i><i></i><span>Verificador oficial del repte · repte-horaris-escola</span></div>
<pre><span class="ordre">$ {html.escape(mostra)}</span>
{chr(10).join(cos)}
<span class="temps">… ({segons:.1f} s)</span></pre>''')


async def main():
    os.makedirs(O, exist_ok=True)
    p = launch(tempfile.mkdtemp(prefix='captura-app-'))
    try:
        t = await Tab.open()
        # Nivell 1
        if NOMES: return await part2(t)
        await carrega(t, '', 'Sí, hi cap'); await t.shot(O + 'a01-portada.png')
        await carrega(t, 'respostes', 'Es mostren'); await t.shot(O + 'a02-respostes.png')
        await t.js(MAIN + '.scrollBy(0, 420)'); await asyncio.sleep(1); await t.shot(O + 'a02-respostes-baix.png')
        await carrega(t, 'respostes?resposta=hores-aula', 'Torna a les respostes')
        await al_centre(t, 'Sense aula assignada a les dades'); await t.shot(O + 'a03-sense-aula.png')
        await carrega(t, 'respostes?resposta=hi-cap-mati', 'Torna a les respostes'); await asyncio.sleep(1.5)
        await t.shot(O + 'a04-hi-cap.png')
        await t.click_text('Detalls informàtics: consulta SQL', sel='summary, p, span'); await asyncio.sleep(1.5)
        await al_centre(t, 'Com ho hem calculat', 'start'); await t.js(MAIN + '.scrollBy(0, -40)'); await asyncio.sleep(0.8)
        await t.shot(O + 'a05-hi-cap-calcul.png')
        await part2(t)
        await resta(t)
    finally:
        p.terminate()


async def part2(t):
        # Nivell 2 · 5.2
        await carrega(t, 'part2', 'La setmana del grup')
        await tria(t, 'p2-titulacio', 'Química'); await tria(t, 'p2-curs', '3')
        await t.wait_text('Grup 21'); await asyncio.sleep(2)
        await t.shot(O + 'a06-p2-grup.png')
        await al_centre(t, '13:30', 'start', quin='shift()'); await asyncio.sleep(1)
        await t.shot(O + 'a07-p2-graella.png')
        # Assistent, sobre la mateixa pantalla
        await t.js("document.querySelector('.xatia-boto').click()"); await asyncio.sleep(0.8)
        await t.shot(O + 'a13-assistent-00-obert.png')
        await t.js("document.querySelector('.xatia textarea').focus()"); await asyncio.sleep(0.3)
        k = 1
        for i, ch in enumerate(PREGUNTA, 1):
            await t.cmd('Input.insertText', text=ch)
            if i % 8 == 0 or i == len(PREGUNTA):
                await t.shot(O + f'a13-assistent-{k:02d}-escriu.png'); k += 1
        await t.cmd('Input.dispatchKeyEvent', type='keyDown', key='Enter', code='Enter', windowsVirtualKeyCode=13, text='\r')
        await t.cmd('Input.dispatchKeyEvent', type='keyUp', key='Enter', code='Enter', windowsVirtualKeyCode=13)
        t0 = time.time(); await asyncio.sleep(0.4)
        await t.shot(O + f'a13-assistent-{k:02d}-pensant.png'); k += 1
        darrer = ''
        while time.time() - t0 < 120:
            ocupat = await t.js("!!document.querySelector('.xatia-pensant, .xatia-escrivint')")
            text = await t.js("document.querySelector('.xatia-conversa').innerText")
            if text != darrer and await t.js("!!document.querySelector('.xatia-escrivint')"):
                await t.shot(O + f'a13-assistent-{k:02d}-escrivint.png'); k += 1; darrer = text
            if not ocupat:
                break
            await asyncio.sleep(0.2)
        await asyncio.sleep(0.6); await t.shot(O + f'a13-assistent-{k:02d}-resposta.png')
        print('resposta en', round(time.time() - t0, 1), 's')
        print(await t.js("document.querySelector('.xatia-conversa').innerText"))


async def resta(t):
        # Junta
        await carrega(t, 'junta', 'Matí, hora més plena'); await t.shot(O + 'a09-junta.png')
        await al_centre(t, 'Excepcions als torns', 'start'); await t.js(MAIN + '.scrollBy(0, -30)'); await asyncio.sleep(0.8)
        await t.shot(O + 'a10-junta-excepcions.png')
        # 5.3 i 5.4
        await carrega(t, 'imprevistos', 'Comprovat amb el verificador oficial'); await t.shot(O + 'a11-imprevistos.png')
        await carrega(t, '', 'Sí, hi cap'); await t.js(MAIN + '.scrollBy(0, 330)'); await asyncio.sleep(1)
        await t.shot(O + 'a12-grau-nou.png')
        # Verificador oficial
        term = os.path.join(O, 'verificador.html'); terminal_html(term)
        await t.goto('file://' + term); await asyncio.sleep(1)
        await t.shot(O + 'a08-verificador.png'); os.remove(term)

asyncio.run(main())

"""Renderitza docs/demo/muntatge/index.html fotograma a fotograma i en fa el vídeo amb ffmpeg.

Ús (des de l'arrel del repositori):
  python docs/demo/eines/render.py                       # vídeo sencer -> docs/demo/demo-general.mp4
  python docs/demo/eines/render.py --mostra 1 4 8 ...     # només uns quants fotogrames (PNG) per revisar
"""
import asyncio, base64, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import launch, Tab

AQUI = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.dirname(AQUI)
HTML = 'file://' + os.path.join(DEMO, 'muntatge', 'index.html') + '?render=1'
FPS, DURADA = 30, 30.0


async def main():
    mostra = sys.argv[2:] if len(sys.argv) > 1 and sys.argv[1] == '--mostra' else None
    perfil = tempfile.mkdtemp(prefix='render-demo-')
    p = launch(perfil)
    try:
        t = await Tab.open()
        await t.goto(HTML)
        for _ in range(100):
            if await t.js("typeof window.llest !== 'undefined'"):
                break
            await asyncio.sleep(0.1)
        await t.js('window.llest')
        if mostra:
            for s in mostra:
                await t.js(f'mostra({float(s)})')
                await t.shot(os.path.join(tempfile.gettempdir(), f'demo-t{s}.png'))
                print(os.path.join(tempfile.gettempdir(), f'demo-t{s}.png'))
            return
        sortida = os.path.join(DEMO, 'demo-general.mp4')
        ff = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                               '-f', 'image2pipe', '-framerate', str(FPS), '-i', '-',
                               '-i', os.path.join(DEMO, 'muntatge', 'veu', 'veu.m4a'),
                               '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
                               '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'copy', '-t', f'{DURADA:.3f}',
                               '-movflags', '+faststart', sortida], stdin=subprocess.PIPE)
        n = int(FPS * DURADA)
        for f in range(n):
            await t.js(f'mostra({f / FPS})')
            r = await t.cmd('Page.captureScreenshot', format='png')
            ff.stdin.write(base64.b64decode(r['data']))
            if f % 90 == 0:
                print(f'{f}/{n}', flush=True)
        ff.stdin.close(); ff.wait()
        print('fet:', sortida)
    finally:
        p.terminate()

asyncio.run(main())

import asyncio, time, sys, tempfile
from cdp import *
Q = 'Quina aula de 60 places està lliure dijous a les 10?'
B = 'http://localhost:8511/'
O = sys.argv[1].rstrip('/') + '/'


async def load(t, path, txt):
    await t.goto(B + path); await t.wait_text(txt); await t.idle(); await asyncio.sleep(2.5); await t.idle()


async def main():
    p = launch(tempfile.mkdtemp(prefix='captura-demo-'))
    try:
        t = await Tab.open()
        await load(t, '?resposta=hores-aula', 'Torna a les respostes')
        await t.js("[...document.querySelectorAll('p')].find(e=>e.innerText.includes('5.722')).scrollIntoView({block:'center'})"); await asyncio.sleep(1)
        await t.shot(O + '01-sense-aula-detall.png')
        await load(t, '', 'Sí, hi cap'); await t.shot(O + '02-portada.png')
        await load(t, 'part2', 'La setmana del grup'); await t.shot(O + '03-horari-grup.png')
        await t.js("document.querySelector('.st-key-p2-vista-aula').scrollIntoView({block:'start'})"); await asyncio.sleep(1)
        x, y = await center(t, ".st-key-p2-aula input"); await mouse_click(t, x, y); await asyncio.sleep(0.8)
        for ch in 'Q2/1005':
            await t.cmd('Input.insertText', text=ch)
        await asyncio.sleep(0.8); x, y = await center(t, "[role=option]"); await mouse_click(t, x, y)
        await t.idle(); await asyncio.sleep(3)
        await t.js("document.querySelector('.st-key-p2-vista-aula').scrollIntoView({block:'start'})"); await asyncio.sleep(1)
        await t.shot(O + '04-horari-aula-Q2-1005.png')
        await load(t, 'imprevistos', 'Comprovat amb el verificador oficial'); await t.shot(O + '05-imprevistos.png')
        await load(t, '', 'Sí, hi cap')
        await t.js("document.querySelector('[data-testid=stMain]').scrollBy(0,330)"); await asyncio.sleep(1)
        await t.shot(O + '06-portada-grau-nou.png')
        await load(t, 'junta', 'Matí, hora més plena'); await t.shot(O + '07-junta.png')
        await load(t, '', 'Sí, hi cap'); await t.shot(O + '08-assistent-00-boto.png')
        await t.js("document.querySelector('.xatia-boto').click()"); await asyncio.sleep(0.7)
        await t.shot(O + '08-assistent-01-obert.png')
        await t.js("document.querySelector('.xatia textarea').focus()"); await asyncio.sleep(0.3)
        k = 2
        for i, ch in enumerate(Q, 1):
            await t.cmd('Input.insertText', text=ch)
            if i % 6 == 0 or i == len(Q):
                await t.shot(O + f'08-assistent-{k:02d}-escriu.png'); k += 1
        await t.cmd('Input.dispatchKeyEvent', type='keyDown', key='Enter', code='Enter', windowsVirtualKeyCode=13, text='\r')
        await t.cmd('Input.dispatchKeyEvent', type='keyUp', key='Enter', code='Enter', windowsVirtualKeyCode=13)
        t0 = time.time(); await asyncio.sleep(0.4)
        await t.shot(O + f'08-assistent-{k:02d}-pensant.png'); k += 1
        last = ''
        while time.time() - t0 < 120:
            busy = await t.js("!!document.querySelector('.xatia-pensant, .xatia-escrivint')")
            txt = await t.js("document.querySelector('.xatia-conversa').innerText")
            if txt != last and await t.js("!!document.querySelector('.xatia-escrivint')"):
                await t.shot(O + f'08-assistent-{k:02d}-escrivint.png'); k += 1; last = txt
            if not busy:
                break
            await asyncio.sleep(0.2)
        await asyncio.sleep(0.5); await t.shot(O + f'08-assistent-{k:02d}-resposta.png')
        print('resposta en', round(time.time() - t0, 1), 's')
        print(await t.js("document.querySelector('.xatia-conversa').innerText"))
    finally:
        p.terminate()

asyncio.run(main())

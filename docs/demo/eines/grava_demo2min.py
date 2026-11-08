"""Vídeo demo de 90 s per a la presentació: un sol pla continu de l'app real (docs/GUIO-VIDEO-DEMO.md).

Cal l'app engegada al port 8511 just abans (launch.json, configuració «demo»), amb la IA real.
Ús (des de l'arrel del repositori):
  python docs/demo/eines/grava_demo90.py            # grava i munta docs/demo/demo-90s.mp4
Les esperes de la IA i de càrrega es fan més curtes al muntatge (es veuen igual, però duren menys).
"""
import asyncio, json, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grava import Pestanya, obre_chrome, munta

URL = os.environ.get('APP_URL', 'http://localhost:8511/')
DEMO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIDA = os.path.join(DEMO, os.environ.get('SORTIDA', 'demo-2min.mp4'))
CSS_W, CSS_H, ESCALA = 1440, 810, 4 / 3  # 1920×1080
PREGUNTA = 'Quantes aules queden lliures dimarts a les 10 a la proposta 5.2?'
ESPERA_IA = 0.9      # durada al vídeo de cada «Pensant…»
ESPERA_PAGINA = 0.5  # durada màxima al vídeo d'una càrrega de pàgina


async def fulla(p, text, quin=0, dins='[data-testid=stMain], [data-testid=stSidebar], .xatia'):
    """Centre de l'element més petit que comença amb `text`."""
    r = await p.js(f"""(() => {{ const t = {json.dumps(text)};
        const ok = (e) => e.innerText && e.innerText.trim().startsWith(t) && e.getClientRects().length;
        const els = [...document.querySelectorAll({json.dumps(dins)})].flatMap(a => [...a.querySelectorAll('*')])
          .filter(ok).filter(e => ![...e.children].some(ok));
        const e = els.at({quin}); if (!e) return null; const r = e.getBoundingClientRect();
        return [r.x + Math.min(r.width, 260) / 2, r.y + r.height / 2, r.y]; }})()""")
    if not r:
        raise RuntimeError('no trobo ' + text)
    return r


async def ves_a(p, text, quin=0, segons=0.9):
    x, y, _ = await fulla(p, text, quin)
    await p.mou(x, y, segons)


async def clica_text(p, text, quin=0, segons=0.9):
    x, y, _ = await fulla(p, text, quin)
    await p.clica(x, y, segons)


async def baixa_fins(p, text, marge=110, segons=1.6, quin=0):
    _, _, y = await fulla(p, text, quin)
    await p.desplaca(y - marge, segons)
    await asyncio.sleep(segons + 0.05)


async def carrega(p, text_final):
    """Espera una càrrega de pàgina; si dura massa, al vídeo s'escurça."""
    t0 = time.time()
    await p.espera_text(text_final); await p.quiet()
    t1 = time.time()
    if t1 - t0 > ESPERA_PAGINA:
        p.marques.append((t0, t1, ESPERA_PAGINA))
    await p.capa()


async def tria(p, selector, text):
    """Obre un desplegable, escriu i tria la primera opció (torna-ho a provar si l'app encara es redibuixa)."""
    await p.quiet(); await asyncio.sleep(0.3)
    for intent in range(3):
        x, y, *_ = await p.on(selector)
        await p.clica(x, y, 0.8 if intent == 0 else 0.3); await asyncio.sleep(0.4)
        await p.escriu(text, 0.09); await asyncio.sleep(0.5)
        for _ in range(30):  # el desplegable pot trigar a mostrar les opcions
            if await p.js("!!document.querySelector('[role=option]')"):
                break
            await asyncio.sleep(0.1)
        if await p.js("!!document.querySelector('[role=option]')"):
            break
        print(f'  {selector}: sense opcions (intent {intent + 1})')
        await p.tecla('Escape', 27); await p.quiet(); await asyncio.sleep(0.5)
    x, y, *_ = await p.on('[role=option]')
    await p.clica(x, y, 0.5)
    t0 = time.time(); await p.quiet(); t1 = time.time()
    if t1 - t0 > ESPERA_PAGINA:
        p.marques.append((t0, t1, ESPERA_PAGINA))
    await p.capa()


async def espera_resposta(p):
    """Espera la resposta de l'assistent; al vídeo, el «Pensant…» dura ESPERA_IA."""
    t0 = time.time(); await asyncio.sleep(0.3)
    while not await p.js("!!document.querySelector('.xatia-escrivint') || !document.querySelector('.xatia-pensant')"):
        await asyncio.sleep(0.05)
    p.marques.append((t0 + 0.3, time.time(), ESPERA_IA))
    while await p.js("!!document.querySelector('.xatia-pensant, .xatia-escrivint')"):
        await asyncio.sleep(0.1)


async def pregunta(p, text):
    await p.escriu(text, 0.03); await asyncio.sleep(0.2)
    await p.tecla('Enter', 13)
    await espera_resposta(p)


REPTE = os.environ.get('REPTE_DIR', '/Users/bernatroca/Bernat/Hackathon/repte/repte-horaris-escola')
ARREL = os.path.dirname(os.path.dirname(REPTE))  # arrel de la carpeta principal del projecte
ORDRE_AVUI = 'python -m horaris check paquet/proposta_partida.csv --semestre 2'
ORDRE_52 = ('python -m horaris check ../../resultats/nivell2/5.2/proposta.csv --semestre 2 '
            '--relaxacions ../../resultats/nivell2/5.2/relaxacions.csv')
PREGUNTA_TERMINAL = 'Quantes aules queden lliures dimarts a les 10?'
ORDRE_IA = ('REPTE_DIR="$PWD/repte/repte-horaris-escola" .venv/bin/python -m app.xat.pregunta '
            f'"{PREGUNTA_TERMINAL}" --proposta 5.2 --setmana típica')


async def ordre_terminal(p, ordre, argv, cwd, nom, env=None, ritme=0.028, espera_max=0.9):
    """Escriu `ordre` al terminal de la gravació i executa de debò `argv` a `cwd`; la sortida és la real."""
    await p.js(f'window.__demo.prompt({json.dumps(nom)})')
    t0, fet = time.time(), 0
    while fet < len(ordre):
        toca = min(len(ordre), int((time.time() - t0) / ritme) + 1)
        if toca > fet:
            await p.js(f'window.__demo.tecleja({json.dumps(ordre[fet:toca])})'); fet = toca
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.35)
    t1 = time.time()
    proc = await asyncio.create_subprocess_exec(*argv, cwd=cwd, env={**os.environ, **(env or {})},
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    primera, sortida = True, []
    while True:
        linia = await proc.stdout.readline()
        if not linia:
            break
        if primera and time.time() - t1 > espera_max:
            p.marques.append((t1, time.time(), espera_max))  # l'espera es veu, però més curta
        primera = False
        text = linia.decode('utf-8').rstrip('\n')
        sortida.append(text)
        await p.js(f'window.__demo.linia({json.dumps(text)})')
        await asyncio.sleep(0.012)
    await proc.wait()
    return sortida


async def verificador(p, ordre, ritme):
    return await ordre_terminal(p, ordre, ['python3'] + ordre.split()[1:], REPTE, 'repte-horaris-escola', ritme=ritme)


def temps_video(p, t):
    t0 = p.fotogrames[0][0]
    return t - t0 - sum((b - a) - d for a, b, d in p.marques if b <= t)


N1 = '<b>Nivell 1</b> · Anàlisi: hi cap el model nou?'
N2 = '<b>Nivell 2 · 5.2</b> · Torns nous'
NV = '<b>Nivell 2</b> · Verificador oficial'
N3 = '<b>Nivell 2 · 5.3</b> · Imprevistos'
NJ = '<b>Nivell 2 · 5.2 i 5.4</b> · Resum per a la Junta'
NIA = '<b>Nivell 3</b> · Assistent d’IA'
N4 = '<b>Nivell 2 · 5.4</b> · Grau nou'
LENT = float(os.environ.get('LENT', '2.08'))  # més temps per llegir cada rètol


def dorm(s):
    return asyncio.sleep(s * LENT)


async def recorregut(p):
    r = p.rotol
    # 0-11 s · Portada (nivell 1)
    await p.part(N1)
    await dorm(0.3)
    await r('1r i 2n al matí: sí, hi cabem', 'Nivell 1 · Anàlisi de dades',
            'A l’hora més plena, 15 de 19 aules ocupades, i en guardem 2 de reserva per a imprevistos')
    await ves_a(p, 'Sí', segons=1.1); await dorm(0.8)
    await ves_a(p, '15 ocupades', segons=0.9); await dorm(1.4)
    await p.desplaca(330, 1.4); await dorm(1.45)
    await r('Avui → amb la proposta', 'Nivell 1 · Anàlisi de dades',
            '2.008 classes fora de torn → 459 excepcions declarades · 4.541 classes sense aula → 0')
    await ves_a(p, 'Avui 2.008', segons=0.8); await dorm(1.1)
    await ves_a(p, 'Avui 4.541', segons=0.8); await dorm(1.3)
    await p.part(N4)
    await r('Hi cap un grau nou de 40 places: sí', 'Nivell 2 · 5.4 Grau nou',
            'L’horari proposat hi col·loca les 235 classes del grau nou sense moure cap classe de la resta')
    await ves_a(p, 'Hi cap un grau nou de 40 places?', segons=0.9); await dorm(3.2)
    await p.part(N1)
    await r('Avui l’horari té 7 tipus de problemes', 'Nivell 1 · Anàlisi de dades',
            'Els més freqüents: classes sense aula, i professorat o alumnat amb dues classes alhora')
    await ves_a(p, 'Quins altres problemes té l’horari d’avui?', segons=0.9); await dorm(3.2)
    # 11-18 s · Com ho sabem
    p.capitols.append(('Com ho sabem', time.time()))
    await p.desplaca(-330, 0.9); await dorm(0.95)
    await r('')  # cap rètol vell sobre la pantalla nova
    await clica_text(p, 'Mira el detall de les aules', segons=0.8)
    await carrega(p, 'Com ho hem calculat')
    await r('Cada xifra explica com s’ha calculat', 'Nivell 1 · Com ho sabem',
            'No hi comptem laboratoris ni dobles titulacions, que no necessiten aula pròpia')
    await dorm(0.2)
    await baixa_fins(p, 'Com ho hem calculat', marge=110, segons=1.4)
    await ves_a(p, 'Comptem les classes', segons=0.6); await dorm(1.3)
    # 18-38 s · Horari proposat (5.2)
    p.capitols.append(('Horari proposat', time.time()))
    await r(''); await p.part('')
    await clica_text(p, 'Mira l’horari proposat', segons=0.8)
    await carrega(p, 'La setmana del grup')
    await p.part(N2)
    await r('1r i 2n al matí; 3r i 4t a la tarda', 'Nivell 2 · 5.2 Torns nous',
            'Cada grup veu la seva setmana i què canvia respecte d’avui')
    await ves_a(p, 'canvis d’hora', segons=0.8); await dorm(0.8)
    await tria(p, '.st-key-p2-curs input', '4')
    await ves_a(p, 'canvis d’hora', segons=0.6); await dorm(0.8)
    x, y, *_ = await p.on('[data-testid=stMain] button', text='Mira l')
    await p.clica(x, y, 0.8); await p.quiet(); await p.capa(); await dorm(0.5)
    x, y, *_ = await p.on('.st-key-p2-controls [data-testid=stExpander] summary')
    await p.clica(x, y, 0.8); await dorm(0.5)
    x, y, *_ = await p.on('.st-key-p2-boto-canvi button')
    await p.clica(x, y, 0.8); await p.quiet(); await p.capa(); await dorm(0.3)
    await r('Cada classe diu on era abans', 'Nivell 2 · 5.2 Torns nous',
            'Grup 430: Computació d’Altes Prestacions passa de dijous 12:30 a dijous 14:30, a la Q3/0009')
    x, y, *_ = await p.on('[data-testid=stMain] button[popovertarget]', text='Computació d')
    await p.desplaca(y - 330, 1.5); await dorm(1.55)
    x, y, *_ = await p.on('[data-testid=stMain] button[popovertarget]', text='Computació d')
    await p.mou(x, y, 0.8); await dorm(0.5)
    await p.clica(x, y, 0.2); await dorm(2.6)
    await p.tecla('Escape', 27); await dorm(0.3)
    await r('')
    # 49-57 s · Imprevistos (5.3)
    p.capitols.append(('Imprevistos', time.time()))
    await clica_text(p, 'Imprevistos', segons=0.9)
    await carrega(p, 'Comprovat amb el verificador oficial')
    await p.part(N3)
    await r('Quatre imprevistos alhora, pocs canvis', 'Nivell 2 · 5.3 Imprevistos',
            'Aula reservada, grup que creix, aula avariada i classe cancel·lada · comprovat amb el verificador')
    await ves_a(p, '65', segons=0.6); await dorm(0.5)
    x, y, *_ = await p.on('[data-testid=stMain] button', text='Mira l')
    await p.desplaca(y - 300, 1.2); await dorm(1.25)
    x, y, *_ = await p.on('[data-testid=stMain] button', text='Mira l')
    await p.clica(x, y, 0.8)
    await p.quiet(); await p.capa(); await dorm(0.4)
    await r('Aula avariada un dia: 6 classes canvien d’aula', 'Nivell 2 · 5.3 Imprevistos',
            'Es fan el mateix dia i a la mateixa hora; només canvia l’aula')
    await baixa_fins(p, 'Què canvia', marge=60, segons=1.0)
    await dorm(2.4)  # que el rètol es llegeixi uns 4,5 s
    # 57-66 s · Resum per a la Junta
    p.capitols.append(('Resum per a la Junta', time.time()))
    await r(''); await p.part('')
    await clica_text(p, 'Resum per a la Junta', segons=0.9)
    await carrega(p, 'Hi cabem a l’hora més plena?')
    await p.part(NJ)
    await r('La Junta decideix amb una pàgina', 'Nivell 2 · Resum per a la Junta',
            'Matí 15 de 19 aules · tarda 18 de 19 · i el grau nou de 40 places també hi cap')
    await ves_a(p, 'Hi cabem a l’hora més plena?', segons=0.8); await dorm(1.3)
    await ves_a(p, 'Hi cap el grau nou de 40 places?', segons=0.9); await dorm(2.0)
    # 66-78 s · Assistent
    p.capitols.append(('Assistent', time.time()))
    x, y, *_ = await p.on('.xatia-boto')
    await p.clica(x, y, 0.8); await dorm(0.4)
    await p.part(NIA)
    await r('Pregunta amb les teves paraules', 'Nivell 3 · Intel·ligència artificial',
            'Respon només amb dades de l’horari, i a «Comprova-ho» hi ha la consulta i les aules que ha trobat')
    x, y, *_ = await p.on('.xatia textarea')
    await p.clica(x, y, 0.4); await dorm(0.1)
    await pregunta(p, PREGUNTA); await dorm(1.1)
    # «Comprova-ho» obre la consulta que ha fet l'assistent i les aules que ha trobat (sense tornar a cridar la IA)
    x, y, *_ = await p.on('.xatia-consultes summary', quin=-1)
    await p.clica(x, y, 0.7); await dorm(0.3)
    p.resposta = await p.js("[...document.querySelectorAll('.xatia-missatge--ia')].map(e => e.innerText).join(' || ')")
    p.comprova = await p.js("[...document.querySelectorAll('.xatia-consultes')].pop().innerText")
    await dorm(2.6)
    await r(''); await p.part('')
    tanca = await p.on('.xatia [data-fa=tanca]')  # tanca el plafó de l'assistent
    if tanca:
        await p.clica(tanca[0], tanca[1], 0.6); await dorm(0.3)
    # 87-91 s · Tancament
    p.capitols.append(('Tancament', time.time()))
    await r(''); await p.part('')
    await clica_text(p, 'Com estem avui', segons=0.6)
    await carrega(p, 'Mira el detall de les aules')
    await dorm(0.8)
    await p.js("window.__demo.negre('Espais de l’Escola', 'Equip Neo')"); await dorm(1.8)


def resposta_bona(text, comprova):
    """La resposta diu N aules i «Comprova-ho» en llista exactament N, sense «No ho puc»."""
    import re
    if re.search(r"No ho puc|No he pogut|incorrect|havia dit|tornat a comprovar", text):
        return False
    n = re.findall(r'(\d+)\s+aules', text.split(' || ')[-1])
    m = re.search(r'Aules: (.+)', comprova or '')
    return bool(n and m) and int(n[0]) == len([a for a in m.group(1).split(',') if a.strip()])


async def presa():
    carpeta = tempfile.mkdtemp(prefix='grava-demo90-')
    chrome = obre_chrome(tempfile.mkdtemp(prefix='perfil-demo90-'), CSS_W, CSS_H, ESCALA)
    try:
        p = await Pestanya.obre(carpeta, CSS_W, CSS_H, ESCALA)
        await p.cmd('Page.navigate', url=URL)
        await p.espera_text('Mira el detall de les aules'); await p.quiet(); await asyncio.sleep(2.5); await p.quiet()
        await p.capa(); await p.js('window.__demo.mou(1180, 640)')
        await p.comenca(); await asyncio.sleep(0.3)
        t_inici = time.time()
        await recorregut(p)
        await asyncio.sleep(0.2); await p.para()
        print(f'gravat: {time.time() - t_inici:.1f} s reals, {len(p.fotogrames)} fotogrames, {len(p.marques)} esperes escurçades')
        for nom, t in p.capitols:
            print(f'  {nom}: {temps_video(p, t):.1f} s')
        print('resposta:', p.resposta)
        print('comprova-ho:', (p.comprova or '').replace(chr(10), ' | '))
        if not resposta_bona(p.resposta, p.comprova):
            return False
        json.dump({'fotogrames': p.fotogrames, 'marques': p.marques}, open(os.path.join(carpeta, 'gravacio.json'), 'w'))
        # Quan surt cada rètol al vídeo (per a la fitxa de rètols)
        rotols = [dict(t=round(temps_video(p, t), 2), tipus=tipus, valor=valor) for t, tipus, valor in p.registre_rotols]
        json.dump(rotols, open(os.path.join(DEMO, 'retols-demo-2min.json'), 'w'), ensure_ascii=False, indent=1)
        durada = munta(p.fotogrames, p.marques, SORTIDA)
        print(f'vídeo: {SORTIDA} · {durada:.2f} s · carpeta de fotogrames: {carpeta}')
        return True
    finally:
        chrome.terminate()
        await asyncio.sleep(1)


async def main():
    # Si la resposta i «Comprova-ho» no quadren, es torna a gravar.
    for intent in range(1, 5):
        print(f'presa {intent}')
        if await presa():
            return
    raise SystemExit('cap presa amb una resposta que quadri amb «Comprova-ho»')

asyncio.run(main())

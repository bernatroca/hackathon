import asyncio, json, base64, subprocess, time, os, itertools, requests, websockets
CHROME=os.path.expanduser('~/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing')
PORT=9333
W,H=1440,900
DPR=int(os.environ.get('DPR','1'))
def launch(profile):
    p=subprocess.Popen([CHROME,'--headless=new',f'--remote-debugging-port={PORT}',f'--user-data-dir={profile}',f'--window-size={W},{H}','--hide-scrollbars','--force-color-profile=srgb','--lang=ca','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            requests.get(f'http://127.0.0.1:{PORT}/json/version',timeout=1); break
        except Exception: time.sleep(0.2)
    return p
class Tab:
    def __init__(s,ws): s.ws=ws; s.ids=itertools.count(1); s.events=[]
    @classmethod
    async def open(cls):
        t=[x for x in requests.get(f'http://127.0.0.1:{PORT}/json').json() if x['type']=='page'][0]
        ws=await websockets.connect(t['webSocketDebuggerUrl'],max_size=2**28)
        tab=cls(ws)
        await tab.cmd('Page.enable'); await tab.cmd('Runtime.enable')
        await tab.cmd('Emulation.setDeviceMetricsOverride',width=W,height=H,deviceScaleFactor=DPR,mobile=False)
        await tab.cmd('Emulation.setEmulatedMedia',features=[{'name':'prefers-color-scheme','value':'light'}])
        return tab
    async def cmd(s,method,**params):
        i=next(s.ids); await s.ws.send(json.dumps({'id':i,'method':method,'params':params}))
        while True:
            m=json.loads(await s.ws.recv())
            if m.get('id')==i:
                if 'error' in m: raise RuntimeError(m['error'])
                return m.get('result',{})
            s.events.append(m)
    async def js(s,expr):
        r=await s.cmd('Runtime.evaluate',expression=expr,awaitPromise=True,returnByValue=True)
        if 'exceptionDetails' in r: raise RuntimeError(r['exceptionDetails'])
        return r['result'].get('value')
    async def goto(s,url): await s.cmd('Page.navigate',url=url)
    async def wait_text(s,text,timeout=60):
        t0=time.time()
        while time.time()-t0<timeout:
            ok=await s.js(f"document.body && document.body.innerText.includes({json.dumps(text)})")
            if ok: return True
            await asyncio.sleep(0.3)
        raise TimeoutError(text)
    async def idle(s,timeout=60):
        # streamlit: wait until no running spinner/status
        t0=time.time(); await asyncio.sleep(0.8)
        while time.time()-t0<timeout:
            busy=await s.js("!!document.querySelector('[data-testid=stStatusWidget]') || !!document.querySelector('[data-testid=stSpinner]')")
            if not busy: return
            await asyncio.sleep(0.3)
    async def shot(s,path,full=False):
        params={'format':'png'}
        if full:
            h=await s.js('Math.max(document.body.scrollHeight, (document.querySelector("[data-testid=stMain]")||document.body).scrollHeight)')
            params.update(captureBeyondViewport=True,clip={'x':0,'y':0,'width':W,'height':h,'scale':1})
        r=await s.cmd('Page.captureScreenshot',**params)
        open(path,'wb').write(base64.b64decode(r['data']))
    async def click_text(s,text,sel='button, a, [role=button], [role=tab], summary, p, span, div'):
        ok=await s.js(f"""(()=>{{const els=[...document.querySelectorAll({json.dumps(sel)})].filter(e=>e.innerText && e.innerText.trim()==={json.dumps(text)} && e.offsetParent);
          if(!els.length) return false; els[els.length-1].scrollIntoView({{block:'center'}}); els[els.length-1].click(); return true}})()""")
        if not ok: raise RuntimeError('no click '+text)

async def mouse_click(t,x,y):
    for typ in ('mouseMoved','mousePressed','mouseReleased'):
        await t.cmd('Input.dispatchMouseEvent',type=typ,x=x,y=y,button='left',clickCount=1)
async def center(t,sel):
    return await t.js(f"(()=>{{const r=document.querySelector({sel!r}).getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()")

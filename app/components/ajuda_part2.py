"""Guia contextual amb focus de teclat i panell al costat de l'apartat."""
import json

import streamlit as st
import streamlit.components.v1 as components
from components.graella import LINIES_JS


PASSOS = (
    ('.st-key-p2-controls', 'Què vols veure?',
     '«Proposta i avui» mostra la proposta i marca els canvis respecte dels fitxers originals. '
     'Amb els imprevistos i el grau nou, es compara amb Torns nous (5.2). El grau nou no té horari anterior. '
     '«Només avui» mostra l’horari original. Tria la proposta; a «Més opcions» pots canviar la setmana.'),
    ('.st-key-p2-seleccio-alumnat', 'De quin grup?',
     'Tria estudis, curs i grup. Incloem la teoria i els seus subgrups de problemes i seminaris. '
     'Dos subgrups simultanis no impliquen que cada estudiant assisteixi a tots dos.'),
    ('.st-key-p2-context-dades', 'Què canvia?',
     'El resum compta canvis de dia o hora, canvis d’una aula que ja hi era, classes que reben aula i aules diferents. '
     'Si faltava l’aula original, assignar-ne una es marca en verd. No és un veredicte de validació.'),
    ('.st-key-p2-clau-colors', 'Filtra per color',
     'Blau: sense canvis. Verd: aula assignada. Taronja: canvia. Ambre: fora del patró. Vermell: excepció demostrada. '
     'A «Més opcions», tria un color per apagar la resta de classes; «Totes» les torna a mostrar.'),
    ('.st-key-p2-graelles .p2-horari', 'Llegeix la setmana',
     'Cada bloc és una classe. Les compartides apareixen juntes. Passa-hi el ratolí o obre el bloc '
     'amb clic o teclat per llegir què hi havia abans. Al mòbil, llisca la graella cap al costat per veure la resta de dies.'),
    ('.st-key-p2-vista-aula', 'Consulta i comparteix una aula',
     'A «Més opcions», mostra totes les classes de l’aula, amb la mateixa setmana i proposta. '
     'Descarrega l’HTML per compartir-lo o imprimir-lo sense connexió.'),
)

# Funció pura exercitada amb rectangles inventats a les proves.
POSICIO_JS = """
function posicioPanell(rect, ample, alt, vw, vh) {
  const marge = 12;
  const limita = y => Math.max(marge, Math.min(y, vh-alt-marge));
  if (vw < 640) return {mode:'estret', left:marge, top:limita(rect.bottom+marge), width:vw-2*marge};
  if (rect.right + ample + 2*marge <= vw)
    return {mode:'dreta', left:rect.right+marge, top:Math.max(marge,Math.min(rect.top,vh-alt-marge)), width:ample};
  if (rect.left >= ample + 2*marge)
    return {mode:'esquerra', left:rect.left-ample-marge, top:limita(rect.top), width:ample};
  const sota = rect.bottom + alt + 2*marge <= vh;
  return {mode:sota?'sota':'damunt', left:Math.max(marge,Math.min(rect.left,vw-ample-marge)),
    top:limita(sota?rect.bottom+marge:rect.top-alt-marge), width:ample};
}
"""


# El popover manual posa el botó a la capa superior del navegador, per damunt
# de la barra lateral i fora del context de container-type del contingut.
CSS_GUIA = """
.st-key-p2-pagina .st-key-p2-obre-guia{position:fixed;left:18px;bottom:18px;right:auto;top:auto;width:max-content;max-width:calc(100vw - 36px);margin:0;padding:0;border:0;background:transparent;overflow:visible;z-index:2147483646;}
.st-key-p2-pagina .st-key-p2-obre-guia button{background:#fff;color:#1d5fae;border:1px solid #d4d3cd;border-radius:12px;padding:10px 14px;min-height:44px;box-shadow:0 2px 8px #0002;cursor:pointer;}
.st-key-p2-pagina .st-key-p2-obre-guia::backdrop{background:transparent;pointer-events:none;}
"""

LLANCADOR_JS = """
      if(window.__p2GuiaLlançadorNeteja)window.__p2GuiaLlançadorNeteja();
      const obre=pagina.querySelector('.st-key-p2-obre-guia');
      if(obre&&typeof obre.showPopover==='function'){
        obre.setAttribute('popover','manual');
        if(!obre.matches(':popover-open'))obre.showPopover();
      }
      let frameObre;
      const situaObre=()=>{
        if(!obre?.isConnected){window.__p2GuiaLlançadorNeteja?.();return;}
        const r=origen(obre);
        obre.style.bottom='auto';obre.style.left=(18-r.left)+'px';
        obre.style.top=(window.innerHeight-obre.offsetHeight-18-r.top)+'px';
      };
      const programaObre=()=>{window.cancelAnimationFrame(frameObre);frameObre=window.requestAnimationFrame(situaObre);};
      window.addEventListener('resize',programaObre);document.addEventListener('scroll',programaObre,true);
      const resizeObre=new window.ResizeObserver(programaObre);
      if(obre)resizeObre.observe(obre);
      resizeObre.observe(pagina);
      const netejaObre=()=>{
        resizeObre.disconnect();window.cancelAnimationFrame(frameObre);window.removeEventListener('resize',programaObre);
        document.removeEventListener('scroll',programaObre,true);
      };
      window.__p2GuiaLlançadorNeteja=netejaObre;
      globalThis.addEventListener('pagehide',()=>{
        if(window.__p2GuiaLlançadorNeteja===netejaObre)netejaObre();
      },{once:true});
      situaObre();
"""


def prova_guia_html():
    """Llançador real en un marc inventat amb menú plegable per a la prova."""
    return """<div class="prova-menu" data-testid="stSidebar">Menú inventat</div>
<button class="prova-obre-menu" aria-expanded="true" aria-controls="prova-contingut">Plega el menú</button>
<div class="st-key-p2-obre-guia"><button type="button" aria-expanded="false" aria-controls="prova-guia">Com funciona? Guia pas a pas</button></div>
<div id="prova-guia" class="prova-panell" hidden role="status">Guia oberta · prova inventada</div>
<script>((window)=>{
 const document=window.document, pagina=document.querySelector('.st-key-p2-pagina');
 const origen=e=>{
   const p=e.offsetParent,r=p?.getBoundingClientRect()||{left:0,top:0};
   return {left:r.left-(p?.scrollLeft||0),top:r.top-(p?.scrollTop||0)};
 };
 LLANCADOR
 const boto=pagina.querySelector('.st-key-p2-obre-guia button');
 boto.onclick=()=>{
   const p=document.getElementById('prova-guia');
   const obert=boto.getAttribute('aria-expanded')!=='true';
   if(typeof p.showPopover==='function'){
     p.hidden=false;p.setAttribute('popover','manual');
     if(obert)p.showPopover();else p.hidePopover();
   }else p.hidden=!obert;
   boto.setAttribute('aria-expanded',String(obert));
 };
 const menu=document.querySelector('.prova-obre-menu');
 menu.onclick=()=>{const plegat=document.body.classList.toggle('menu-plegat');menu.setAttribute('aria-expanded',String(!plegat));menu.textContent=plegat?'Obre el menú':'Plega el menú';};
})(window)</script>""".replace('LLANCADOR', LLANCADOR_JS)


def _pas(valor):
    st.session_state['p2-guia-pas'] = valor


def mostra_guia():
    with st.container(key='p2-obre-guia'):
        st.button('Com funciona? Guia pas a pas', key='p2-inicia-guia', on_click=_pas, args=(0,))
    pas = st.session_state.get('p2-guia-pas')
    if pas is None:
        return
    _, titol, text = PASSOS[pas]
    with st.container(key='p2-guia'):
        st.caption(f'Guia · Pas {pas + 1} de {len(PASSOS)}')
        st.markdown(f'<div aria-live="polite"><h3 id="p2-titol-guia">{titol}</h3><p>{text}</p></div>', unsafe_allow_html=True)
        abans, despres, tanca = st.columns(3)
        abans.button('Anterior', key='p2-guia-anterior', disabled=pas == 0, on_click=_pas, args=(max(0, pas - 1),))
        despres.button('Acaba' if pas == len(PASSOS) - 1 else 'Següent', key='p2-guia-seguent',
            on_click=_pas, args=(None if pas == len(PASSOS) - 1 else pas + 1,))
        tanca.button('Tanca', key='p2-guia-tanca', on_click=_pas, args=(None,))


def enfoca_pas():
    pas = st.session_state.get('p2-guia-pas')
    selector = PASSOS[pas][0] if pas is not None else None
    # components.html admet alçada zero i executa scripts al mateix origen.
    # Tots els selectors, events i coordenades pertanyen al document pare.
    # Es netegen listeners i observadors a cada renderitzat, també en filtrar.
    script = """<script>((window)=>{
      const document=window.document;
      if(window.__p2GuiaNeteja)window.__p2GuiaNeteja();
      const pagina=document.querySelector('.st-key-p2-pagina');
      if(!pagina)return;
      LINIES
      window.__p2LiniesNeteja?.();
      const netejaLinies=preparaLiniesHorari(pagina,window);
      window.__p2LiniesNeteja=netejaLinies;
      globalThis.addEventListener('pagehide',()=>{
        if(window.__p2LiniesNeteja===netejaLinies)netejaLinies();
      },{once:true});
      // El CSS comú usa container-type: el bloc pot ser el containing block
      // dels elements fixed. Compensem-ne l'origen per mantenir coordenades de viewport.
      const origen=e=>{
        const parent=e.offsetParent;
        const r=parent?.getBoundingClientRect()||{left:0,top:0};
        return {left:r.left-(parent?.scrollLeft||0),top:r.top-(parent?.scrollTop||0)};
      };
      LLANCADOR
      const selector=SELECTOR, pas=PAS;
      pagina.querySelectorAll('.p2-pas-actiu').forEach(e=>e.classList.remove('p2-pas-actiu'));
      if(!selector){window.__p2GuiaPas=null;return;}
      POSICIO
      let objectiu,panell,observer,resizeObserver,frame,acabat=false;
      const redueix=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const situa=()=>{
        if(!objectiu?.isConnected||!panell?.isConnected)return;
        const rect=objectiu.getBoundingClientRect();
        const ample=Math.min(350,window.innerWidth-24);
        panell.style.width=ample+'px';
        const pos=posicioPanell(rect,ample,panell.offsetHeight,window.innerWidth,window.innerHeight);
        panell.dataset.posicio=pos.mode;
        panell.style.width=pos.width+'px';
        panell.style.position='fixed';
        const r=origen(panell);
        panell.style.left=(pos.left-r.left)+'px';panell.style.top=(pos.top-r.top)+'px';
      };
      const programa=()=>{window.cancelAnimationFrame(frame);frame=window.requestAnimationFrame(situa);};
      const esc=e=>{
        if(e.key==='Escape'){
          e.preventDefault();
          pagina.querySelector('.st-key-p2-guia-tanca button')?.click();
          pagina.querySelector('.st-key-p2-inicia-guia button')?.focus();
        }
      };
      const inicia=()=>{
        objectiu=pagina.querySelector(selector);panell=pagina.querySelector('.st-key-p2-guia');
        if(!objectiu||!panell)return false;
        objectiu.classList.add('p2-pas-actiu');
        panell.setAttribute('role','dialog');panell.setAttribute('aria-labelledby','p2-titol-guia');
        panell.setAttribute('tabindex','-1');
        const nou=window.__p2GuiaPas!==pas;
        window.__p2GuiaPas=pas;
        if(nou)objectiu.scrollIntoView({behavior:redueix?'instant':'smooth',block:'start'});
        situa();
        if(nou){
          panell.focus({preventScroll:true});
        }
        observer?.disconnect();
        resizeObserver=new window.ResizeObserver(programa);resizeObserver.observe(objectiu);resizeObserver.observe(panell);
        acabat=true;return true;
      };
      window.addEventListener('resize',programa);document.addEventListener('scroll',programa,true);
      document.addEventListener('keydown',esc);
      if(!inicia()){
        observer=new window.MutationObserver(()=>{if(!acabat)inicia();});
        observer.observe(pagina,{childList:true,subtree:true});
      }
      const neteja=()=>{
        objectiu?.classList.remove('p2-pas-actiu');observer?.disconnect();resizeObserver?.disconnect();
        window.cancelAnimationFrame(frame);window.removeEventListener('resize',programa);
        document.removeEventListener('scroll',programa,true);document.removeEventListener('keydown',esc);
      };
      window.__p2GuiaNeteja=neteja;
      // El document de l'iframe desapareix també en navegar a una altra pàgina.
      globalThis.addEventListener('pagehide',()=>{
        if(window.__p2GuiaNeteja===neteja){
          neteja();
        }
      },{once:true});
    })(window.parent)</script>"""
    components.html(script.replace('SELECTOR', json.dumps(selector)).replace('PAS;', json.dumps(pas) + ';')
        .replace('POSICIO', POSICIO_JS).replace('LLANCADOR', LLANCADOR_JS).replace('LINIES', LINIES_JS), height=0, scrolling=False, tab_index=-1)

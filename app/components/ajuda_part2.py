"""Guia contextual amb focus de teclat i panell al costat de l'apartat."""
import json

import streamlit as st


PASSOS = (
    ('.st-key-p2-seleccio-proposta', 'Què vols veure?',
     '«Proposta i avui» mostra la proposta i marca els canvis respecte dels fitxers originals. '
     '«Només avui» mostra l’horari original. Tria també la proposta i la setmana.'),
    ('.st-key-p2-seleccio-alumnat', 'De quin grup?',
     'Tria estudis, curs i grup. Incloem la teoria i els seus subgrups de problemes i seminaris. '
     'Dos subgrups simultanis no impliquen que cada estudiant assisteixi a tots dos.'),
    ('.st-key-p2-context-dades', 'Què canvia?',
     'El resum compta canvis de dia o hora, canvis d’una aula que ja hi era i aules diferents. '
     'Si faltava l’aula original, assignar-ne una es marca en verd. No és un veredicte de validació.'),
    ('.st-key-p2-clau-colors', 'Filtra per color',
     'Blau: sense canvis. Verd: aula assignada. Taronja: canvia. Vermell: cas especial. '
     'Tria una pastilla per apagar la resta de classes; «Totes» les torna a mostrar.'),
    ('.st-key-p2-graelles .horari-scroll', 'Llegeix la setmana',
     'Cada bloc és una classe. Les compartides apareixen juntes. Passa-hi el ratolí o obre el bloc '
     'amb clic o teclat per llegir què hi havia abans. Si no hi cap, desplaça la graella lateralment.'),
    ('.st-key-p2-vista-aula', 'Consulta i comparteix una aula',
     'Mostra totes les classes de l’aula, amb la mateixa setmana i proposta. '
     'Descarrega l’HTML per compartir-lo o imprimir-lo sense connexió.'),
)

# Funció pura exercitada amb rectangles inventats a les proves.
POSICIO_JS = """
function posicioPanell(rect, ample, alt, vw, vh) {
  const marge = 12;
  if (vw < 640) return {mode:'estret', left:marge, top:Math.max(marge,vh-alt-marge), width:vw-2*marge};
  if (rect.right + ample + 2*marge <= vw)
    return {mode:'dreta', left:rect.right+marge, top:Math.max(marge,Math.min(rect.top,vh-alt-marge)), width:ample};
  return {mode:'sota', left:Math.max(marge,Math.min(rect.left,vw-ample-marge)), top:rect.bottom+marge, width:ample};
}
"""


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
    # st.html executa el script al document de Streamlit (sense iframe).
    # Es netegen listeners i observadors a cada renderitzat, també en filtrar.
    script = """<script>(()=>{
      if(window.__p2GuiaNeteja)window.__p2GuiaNeteja();
      const pagina=document.querySelector('.st-key-p2-pagina');
      if(!pagina)return;
      // El CSS comú usa container-type: el bloc pot ser el containing block
      // dels elements fixed. Compensem-ne l'origen per mantenir coordenades de viewport.
      const origen=e=>{
        const parent=e.offsetParent;
        const r=parent?.getBoundingClientRect()||{left:0,top:0};
        return {left:r.left-(parent?.scrollLeft||0),top:r.top-(parent?.scrollTop||0)};
      };
      if(window.__p2GuiaLlançadorNeteja)window.__p2GuiaLlançadorNeteja();
      const obre=pagina.querySelector('.st-key-p2-obre-guia');
      let frameObre;
      const situaObre=()=>{
        if(!obre?.isConnected){window.__p2GuiaLlançadorNeteja?.();return;}
        const r=origen(obre);
        obre.style.bottom='auto';obre.style.left=(18-r.left)+'px';
        obre.style.top=(innerHeight-obre.offsetHeight-18-r.top)+'px';
      };
      const programaObre=()=>{cancelAnimationFrame(frameObre);frameObre=requestAnimationFrame(situaObre);};
      addEventListener('resize',programaObre);document.addEventListener('scroll',programaObre,true);
      window.__p2GuiaLlançadorNeteja=()=>{
        cancelAnimationFrame(frameObre);removeEventListener('resize',programaObre);
        document.removeEventListener('scroll',programaObre,true);
      };
      situaObre();
      const selector=SELECTOR, pas=PAS;
      pagina.querySelectorAll('.p2-pas-actiu').forEach(e=>e.classList.remove('p2-pas-actiu'));
      if(!selector){window.__p2GuiaPas=null;return;}
      POSICIO
      let objectiu,panell,observer,resizeObserver,frame,acabat=false;
      const redueix=matchMedia('(prefers-reduced-motion: reduce)').matches;
      const situa=()=>{
        if(!objectiu?.isConnected||!panell?.isConnected)return;
        const rect=objectiu.getBoundingClientRect();
        const ample=Math.min(350,innerWidth-24);
        const pos=posicioPanell(rect,ample,panell.offsetHeight,innerWidth,innerHeight);
        panell.dataset.posicio=pos.mode;
        panell.style.width=pos.width+'px';
        if(pos.mode==='sota'){
          // Coordenades relatives al contenidor posicionat de Streamlit.
          panell.style.position='absolute';
          const r=origen(panell);
          panell.style.left=(pos.left-r.left)+'px';
          panell.style.top=(pos.top-r.top)+'px';
        }else{
          panell.style.position='fixed';
          const r=origen(panell);
          panell.style.left=(pos.left-r.left)+'px';panell.style.top=(pos.top-r.top)+'px';
        }
      };
      const programa=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(situa);};
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
          // En mode sota, el panell continua dins del flux desplaçable de la pàgina.
          if(panell.dataset.posicio==='sota')panell.scrollIntoView({behavior:redueix?'instant':'smooth',block:'nearest'});
        }
        observer?.disconnect();
        resizeObserver=new ResizeObserver(programa);resizeObserver.observe(objectiu);resizeObserver.observe(panell);
        acabat=true;return true;
      };
      addEventListener('resize',programa);document.addEventListener('scroll',programa,true);
      document.addEventListener('keydown',esc);
      if(!inicia()){
        observer=new MutationObserver(()=>{if(!acabat)inicia();});
        observer.observe(pagina,{childList:true,subtree:true});
      }
      window.__p2GuiaNeteja=()=>{
        objectiu?.classList.remove('p2-pas-actiu');observer?.disconnect();resizeObserver?.disconnect();
        cancelAnimationFrame(frame);removeEventListener('resize',programa);
        document.removeEventListener('scroll',programa,true);document.removeEventListener('keydown',esc);
      };
    })()</script>"""
    st.html(script.replace('SELECTOR', json.dumps(selector)).replace('PAS;', json.dumps(pas) + ';')
        .replace('POSICIO', POSICIO_JS), unsafe_allow_javascript=True)

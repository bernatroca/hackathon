"""Ajuda opcional que recorre els apartats reals de la pàgina."""
import json

import streamlit as st


PASSOS = (
    ('p2-proposta', 'Què vols comparar?',
     'L’horari actual és el que consta als fitxers originals. Una proposta és una possible millora. '
     'La d’assignar aules conserva els dies i les hores; les altres poden reorganitzar-los. '
     'Si només vols consultar les dades originals, tria «Només l’horari actual».'),
    ('p2-alumnat', 'De quins estudiants vols veure l’horari?',
     'Tria la titulació i el curs. Pots consultar tots els cursos, amb classes al matí o a la tarda. '
     'Si hi ha diversos grups d’estudiants, també en podràs triar un. '
     'La graella inclou la teoria i els seus subgrups de problemes i seminaris.'),
    ('p2-dades', 'Per què pot faltar l’aula?',
     '«Aula no indicada a les dades» vol dir que el fitxer original no diu on es fa aquella classe. '
     'No vol dir que la classe no es faci. La proposta pot completar aquesta informació assignant-li una aula.'),
    ('p2-llegenda', 'Què vol dir cada color?',
     'Blau: es conserva la classe. Verd: la proposta hi afegeix una aula. '
     'Groc: canvia el dia, l’hora o una aula que ja tenia. Una vora discontínua assenyala un cas especial. '
     'Les classes també porten el canvi escrit: no cal distingir els colors per entendre-les.'),
    ('p2-horaris', 'Com es llegeix la setmana?',
     'Els dies són a les columnes i les hores a les files. Un bloc llarg és una sola classe que dura més estona. '
     'Els blocs simultanis poden correspondre a subgrups diferents. '
     'Compara «Horari actual» amb «Amb la proposta»; en una pantalla petita apareixen un sota l’altre.'),
    ('p2-aula', 'I si vols consultar una aula?',
     'Aquest apartat mostra totes les classes que ocuparien l’aula triada aquella setmana. '
     'Fa servir el mateix horari i la mateixa setmana que has triat a dalt. '
     'Pots descarregar-lo per compartir-lo o imprimir-lo.'),
)


def _pas(valor):
    st.session_state['p2-guia-pas'] = valor
    st.session_state.pop('p2-guia-enfocat', None)


def mostra_guia():
    st.markdown('''<style>
    .block-container:has(.st-key-p2-pagina){max-width:2000px}
    .st-key-p2-guia{position:fixed;right:20px;bottom:20px;width:min(440px,calc(100vw - 40px));max-height:calc(100vh - 40px);overflow:auto;z-index:10000;background:white;border:2px solid #256abf;border-radius:14px;padding:18px;box-shadow:0 6px 30px #0003}
    .st-key-p2-guia h3{font-size:22px!important}
    .st-key-p2-guia [data-testid="stHorizontalBlock"]{flex-wrap:nowrap;gap:8px}
    .st-key-p2-guia [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important;width:auto!important}
    .p2-pas-actiu{outline:3px solid #256abf;outline-offset:5px;border-radius:8px}
    [id^="p2-"]{scroll-margin-top:24px}
    </style>''', unsafe_allow_html=True)
    st.button('Com funciona? Guia pas a pas', key='p2-inicia-guia', on_click=_pas, args=(0,))
    pas = st.session_state.get('p2-guia-pas')
    if pas is None:
        return
    desti, titol, text = PASSOS[pas]
    with st.container(key='p2-guia'):
        st.caption(f'Guia · Pas {pas + 1} de {len(PASSOS)}')
        st.markdown(f'<div aria-live="polite"><h3>{titol}</h3><p>{text}</p></div>', unsafe_allow_html=True)
        st.markdown(f'[Vés a aquest apartat](#{desti})')
        abans, despres, tanca = st.columns(3)
        abans.button('Anterior', key='p2-guia-anterior', disabled=pas == 0, on_click=_pas, args=(max(0, pas - 1),))
        ultim = pas == len(PASSOS) - 1
        despres.button('Acaba' if ultim else 'Següent', key='p2-guia-seguent', on_click=_pas, args=(None if ultim else pas + 1,))
        tanca.button('Tanca', key='p2-guia-tanca', on_click=_pas, args=(None,))


def enfoca_pas():
    """Desplaçament només en avançar la guia, mai quan es canvia un filtre."""
    pas = st.session_state.get('p2-guia-pas')
    if st.session_state.get('p2-guia-enfocat', 'inicial') == pas:
        return
    st.session_state['p2-guia-enfocat'] = pas
    desti = PASSOS[pas][0] if pas is not None else None
    # Només s'interpolen identificadors fixos de PASSOS, mai contingut de les dades.
    st.html('''<script>(()=>{
      document.querySelectorAll('.p2-pas-actiu').forEach(e=>e.classList.remove('p2-pas-actiu'));
      const id=''' + json.dumps(desti) + ''';
      if(!id)return;
      let observer;
      const mostra=()=>{
        const ancora=document.getElementById(id);
        if(!ancora)return false;
        const apartat=ancora.closest('[data-testid="stVerticalBlock"]')||ancora;
        apartat.classList.add('p2-pas-actiu');
        apartat.setAttribute('tabindex','-1');
        apartat.focus({preventScroll:true});
        apartat.scrollIntoView({behavior:'instant',block:'start'});
        if(observer)observer.disconnect();
        return true;
      };
      if(!mostra()){
        observer=new MutationObserver(mostra);
        observer.observe(document.body,{childList:true,subtree:true});
        setTimeout(()=>observer.disconnect(),3000);
      }
    })()</script>''', unsafe_allow_javascript=True)

/* Xat amb la IA: un botó baix a la dreta que obre un plafó a la dreta, que es pot fer gran.
   JavaScript sense framework, per posar-lo a qualsevol web (també la d'un programa en Python).

   Fet a partir de l'estilista d'Armari (src/components/Estilista.tsx i Xat.tsx).

     <link rel="stylesheet" href="xat-ia.css">
     <script src="xat-ia.js"></script>
     <script>
       XatIA.inicia({
         api: '/api/xat',
         titol: 'Assistent',
         salutacio: 'Hola! Pregunta’m el que vulguis…',
         preguntes: ['Què puc fer aquí?', 'Explica’m aquesta pantalla'],
       });
       // Quan canvia el que es veu al programa:
       XatIA.pantalla({ resum: 'Factura 123', text: 'Mira la factura 123 de Joan…', preguntes: [...] });
     </script>

   API:
     XatIA.inicia(opcions)    crea el botó i el plafó (un sol cop)
     XatIA.pantalla(p|null)   què hi ha a la pantalla: {resum, text, preguntes?}
     XatIA.obre(pregunta?)    obre el xat i, si cal, fa la pregunta
     XatIA.tanca()
     XatIA.conversaNova()
*/
(function () {
  'use strict';

  const PER_DEFECTE = {
    api: '/api/xat',
    titol: 'Assistent',
    salutacio: 'Hola! Pregunta’m el que vulguis. Em pots passar captures de pantalla amb el botó de la imatge, enganxant-les (Cmd+V) o arrossegant-les aquí.',
    /* Una llista, o una funció (pantalla) => llista. */
    preguntes: [],
    /* Dades fixes per al primer missatge (string o funció). Queden fixes fins a una conversa nova. */
    context: undefined,
    clauMemoria: 'xat-ia',
    maxCaptures: 3,
    /* Costat llarg màxim de cada captura, en píxels: prou perquè es llegeixi el text. */
    midaCaptura: 1600,
    preguntaNomesCaptura: 'Mira aquesta captura i digues-me què hi veus.',
  };

  /* Icones de Lucide (lucide.dev, llicència ISC), en línia perquè no calgui res més. */
  const ICONES = {
    sparkles: '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    gran: '<path d="M15 3h6v6"/><path d="m21 3-7 7"/><path d="m3 21 7-7"/><path d="M9 21H3v-6"/>',
    petit: '<path d="m14 10 7-7"/><path d="M20 10h-6V4"/><path d="m3 21 7-7"/><path d="M4 14h6v6"/>',
    nova: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    imatge: '<path d="M16 5h6"/><path d="M19 2v6"/><path d="M21 11.5V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7.5"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/><circle cx="9" cy="9" r="2"/>',
    envia: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
  };
  const icona = (nom, mida = 18) =>
    `<svg width="${mida}" height="${mida}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONES[nom]}</svg>`;

  let op; // opcions
  let el = {}; // elements
  const estat = {
    missatges: [], // {role, content, pantalla?, imatges?: [dataUri], fotos?: n}
    contextInicial: undefined,
    feina: false,
    parcial: '',
    eina: '',
    estatResposta: '',
    error: '',
    obert: false,
    gran: false,
    pantalla: null,
    preparades: [], // captures a punt d'enviar
    preparant: 0,
    avis: '',
    llesta: true, // la IA, segons el GET de salut
  };

  const esMobil = () => window.matchMedia('(max-width: 699px)').matches;

  /* ---------- memòria: la conversa es recorda en aquest navegador, sense les captures ---------- */

  function llegeixMemoria() {
    try {
      const desat = JSON.parse(localStorage.getItem(op.clauMemoria) || 'null');
      if (desat && Array.isArray(desat.missatges)) {
        estat.missatges = desat.missatges;
        estat.contextInicial = desat.contextInicial;
      }
      estat.gran = localStorage.getItem(op.clauMemoria + '.gran') === '1';
    } catch (e) {
      /* res desat, o malmès: es comença de nou */
    }
  }

  function desa() {
    try {
      if (!estat.missatges.length) return localStorage.removeItem(op.clauMemoria);
      /* Les captures no hi caben: en queda el nombre. */
      const missatges = estat.missatges.map(({ imatges, ...m }) => (imatges && imatges.length ? { ...m, fotos: imatges.length } : m));
      localStorage.setItem(op.clauMemoria, JSON.stringify({ missatges, contextInicial: estat.contextInicial }));
    } catch (e) {
      /* sense espai: la conversa dura mentre la pàgina és oberta */
    }
  }

  /* ---------- el que va a la IA ---------- */

  function textPerALaIA(m, i) {
    let t = m.content;
    if (m.role === 'assistant' && Array.isArray(m.consultes) && m.consultes.length) {
      const consultes = m.consultes.map((c) => ({
        eina: c.eina, args: c.args, ok: c.ok, resultat: c.resultat,
        id_sessio: Array.isArray(c.id_sessio) ? c.id_sessio.slice(0, 10) : [],
      }));
      // El JSON no pot tancar el delimitador ni afegir altres blocs de context.
      const dades = JSON.stringify(consultes).replace(/[<>&]/g, (c) =>
        ({'<': '\\u003c', '>': '\\u003e', '&': '\\u0026'})[c]);
      t += `\n\n<consultes_anteriors>\n${dades}\n</consultes_anteriors>`;
    }
    if (m.pantalla) t = `<pantalla>\n${m.pantalla}\n</pantalla>\n\n${t}`;
    if (i === 0 && estat.contextInicial) t = `<context>\n${estat.contextInicial}\n</context>\n\n${t}`;
    return t;
  }

  /* Les captures només van amb l'última pregunta: les d'abans la IA ja les ha vistes, i
     tornar-les a enviar es pagaria a cada pregunta. */
  function perAlServidor() {
    const ultima = estat.missatges.map((m) => m.role).lastIndexOf('user');
    return estat.missatges.map((m, i) => {
      const text = textPerALaIA(m, i);
      const quantes = (m.imatges && m.imatges.length) || m.fotos || 0;
      if (i === ultima && m.imatges && m.imatges.length) {
        return { role: m.role, content: [{ type: 'text', text }, ...m.imatges.map((url) => ({ type: 'image_url', image_url: { url } }))] };
      }
      return { role: m.role, content: quantes ? `${text}\n\n[Amb ${quantes === 1 ? 'una captura' : quantes + ' captures'}, que ja has vist.]` : text };
    });
  }

  /* ---------- enviar ---------- */

  async function envia(textCru, desDeLaCaixa) {
    if (estat.feina || estat.preparant) return;
    const captures = desDeLaCaixa ? estat.preparades : [];
    const text = textCru.trim() || (captures.length ? op.preguntaNomesCaptura : '');
    if (!text) return;
    if (!estat.llesta) {
      estat.error = 'La IA encara no està a punt. Torna-ho a provar més tard.';
      return pinta();
    }

    const abans = estat.missatges;
    const primera = !abans.length;
    if (primera) estat.contextInicial = typeof op.context === 'function' ? op.context() : op.context;
    const pregunta = { role: 'user', content: text };
    if (estat.pantalla && estat.pantalla.text) pregunta.pantalla = estat.pantalla.text;
    if (captures.length) pregunta.imatges = captures;
    estat.missatges = [...abans, pregunta];
    if (desDeLaCaixa) {
      el.caixa.value = '';
      estat.preparades = [];
    }
    estat.avis = '';
    estat.error = '';
    estat.feina = true;
    estat.parcial = '';
    estat.eina = '';
    estat.estatResposta = '';
    desa();
    pinta();

    try {
      const r = await pregunta_(perAlServidor());
      estat.missatges = [...estat.missatges, { role: 'assistant', content: r.text, consultes: r.consultes }];
      if (r.error) estat.error = r.error;
      else if (r.tallada) estat.error = 'La resposta s’ha tallat per llarga. Prova una pregunta més concreta.';
    } catch (e) {
      /* La pregunta que ha fallat no es queda: el text i les captures tornen a la caixa. */
      estat.missatges = abans;
      if (primera) estat.contextInicial = undefined;
      if (desDeLaCaixa || !el.caixa.value) el.caixa.value = textCru;
      if (desDeLaCaixa) estat.preparades = captures;
      estat.error = e && e.message ? e.message : String(e);
    } finally {
      estat.feina = false;
      estat.parcial = '';
      estat.eina = '';
      estat.estatResposta = '';
      desa();
      pinta();
      creixCaixa();
    }
  }

  /* El POST: si torna text/event-stream, es llegeix en directe; si no, és un error en JSON. */
  async function pregunta_(missatges) {
    let resposta;
    try {
      resposta = await fetch(op.api, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ missatges }),
      });
    } catch (e) {
      throw new Error('No hi ha connexió amb el servidor.');
    }
    const tipus = resposta.headers.get('content-type') || '';
    if (resposta.ok && resposta.body && tipus.includes('event-stream')) return llegeixFlux(resposta.body);
    const dades = await resposta.json().catch(() => null);
    throw new Error(missatgeError(dades && dades.error, resposta.status));
  }

  function missatgeError(missatge, codi) {
    const text = typeof missatge === 'string' ? missatge : '';
    if (codi === 429 || /\b429\b/.test(text)) return 'La IA està saturada. Torna-ho a provar d’aquí a uns segons.';
    if ([401, 403, 404, 424].includes(codi) || /\bHTTP\s+(401|403|404)\b/i.test(text) || /no està ben configurat/i.test(text)) return 'L’assistent no està ben configurat (clau o model del fitxer .env). Avisa qui manté l’app.';
    if (codi >= 500 || /\bHTTP\s+5\d\d\b/i.test(text)) return 'El servei de l’assistent no està disponible ara mateix. Torna-ho a provar d’aquí a uns segons.';
    return text || 'No s’ha pogut completar la consulta. Torna-ho a provar.';
  }

  async function llegeixFlux(cos) {
    const lector = cos.getReader();
    const descodifica = new TextDecoder();
    let text = '';
    let consultes = [];
    let pendent = '';
    let darrer = 0;
    const interromput = (error = 'La connexió s’ha tallat a mig resposta. Torna-ho a provar.') => {
      if (text) return { text, consultes, tallada: false, error };
      throw new Error(error);
    };
    for (;;) {
      let lectura;
      try {
        lectura = await lector.read();
      } catch (e) {
        return interromput();
      }
      const { value, done } = lectura;
      if (value) pendent += descodifica.decode(value, { stream: true });
      const blocs = pendent.split('\n\n');
      pendent = done ? '' : blocs.pop() || '';
      for (const bloc of blocs) {
        const dada = bloc.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim()).join('');
        if (!dada) continue;
        let e;
        try {
          e = JSON.parse(dada);
        } catch (err) {
          continue;
        }
        if (e.error) return interromput(missatgeError(e.error));
        if (Array.isArray(e.consultes)) consultes = e.consultes;
        if (e.estat === 'Comprovant la resposta…') {
          estat.estatResposta = e.estat;
          pintaConversa();
        }
        if (e.eina) {
          estat.eina = String(e.eina);
          estat.estatResposta = '';
          estat.parcial = text;
          pintaConversa();
        }
        if (typeof e.tros === 'string') {
          text += e.tros;
          /* Com a molt vint cops per segon: pintar-ho a cada tros no cal. */
          const ara = performance.now();
          if (ara - darrer > 50) {
            darrer = ara;
            estat.parcial = text;
            pintaConversa();
          }
        }
        if (e.fi) {
          if (!text) throw new Error(e.tallada
            ? 'La resposta s’ha tallat abans d’escriure res. Prova una pregunta més concreta.'
            : 'No s’ha pogut obtenir una resposta. Torna-ho a provar.');
          return { text, consultes, tallada: !!e.tallada, model: e.model };
        }
      }
      if (done) break;
    }
    return interromput('La connexió s’ha tallat abans de completar la resposta. Torna-ho a provar.');
  }

  /* ---------- captures ---------- */

  async function afegeixCaptures(llista) {
    const imatges = [...llista].filter((f) => f.type && f.type.startsWith('image/'));
    if (!imatges.length) return;
    const lloc = op.maxCaptures - estat.preparades.length;
    const triades = imatges.slice(0, Math.max(0, lloc));
    estat.avis = imatges.length > lloc ? `Com a molt ${op.maxCaptures} captures per pregunta.` : '';
    estat.preparant++;
    pinta();
    try {
      const noves = await Promise.all(triades.map((f) => redueix(f, op.midaCaptura)));
      estat.preparades = [...estat.preparades, ...noves].slice(0, op.maxCaptures);
    } catch (e) {
      estat.avis = 'No he pogut llegir aquesta imatge.';
    } finally {
      estat.preparant--;
      pinta();
    }
  }

  /* JPEG amb el costat llarg com a molt `max`: una captura de 5 MB en queda una de ~300 KB. Fons
     blanc, per si la PNG té transparències. */
  async function redueix(fitxer, max) {
    const bitmap = await createImageBitmap(fitxer);
    const escala = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
    const llenc = document.createElement('canvas');
    llenc.width = Math.round(bitmap.width * escala);
    llenc.height = Math.round(bitmap.height * escala);
    const ctx = llenc.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, llenc.width, llenc.height);
    ctx.drawImage(bitmap, 0, 0, llenc.width, llenc.height);
    bitmap.close && bitmap.close();
    return llenc.toDataURL('image/jpeg', 0.85);
  }

  /* ---------- text de la IA: un markdown petit i segur (res d'HTML que vingui de fora) ---------- */

  const escapa = (s) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  function enLinia(s) {
    return escapa(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  }

  function markdown(text) {
    // Una sola passada i només les entitats conegudes. enLinia ho torna a
    // escapar abans de generar HTML, també durant la resposta en directe.
    const entitats = { '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"', '&#39;': "'", '&#x27;': "'" };
    text = text.replace(/&(?:lt|gt|amp|quot|#39|#x27);/g, (entitat) => entitats[entitat]);
    text = text.replace(/<consultes_anteriors>[\s\S]*?(?:<\/consultes_anteriors>|$)/g, '');
    const linies = text.replace(/\r/g, '').split('\n');
    let html = '';
    let llista = null; // 'ul' | 'ol'
    let paragraf = [];
    const tancaParagraf = () => {
      if (paragraf.length) html += `<p>${paragraf.map(enLinia).join('<br>')}</p>`;
      paragraf = [];
    };
    const tancaLlista = () => {
      if (llista) html += `</${llista}>`;
      llista = null;
    };
    for (const linia of linies) {
      const punt = /^\s*[-*•]\s+(.*)$/.exec(linia);
      const num = /^\s*\d+[.)]\s+(.*)$/.exec(linia);
      const titol = /^#{1,4}\s+(.*)$/.exec(linia);
      if (punt || num) {
        tancaParagraf();
        const tipus = punt ? 'ul' : 'ol';
        if (llista !== tipus) {
          tancaLlista();
          html += `<${tipus}>`;
          llista = tipus;
        }
        html += `<li>${enLinia((punt || num)[1])}</li>`;
      } else if (titol) {
        tancaParagraf();
        tancaLlista();
        html += `<p class="xatia-titolet">${enLinia(titol[1])}</p>`;
      } else if (!linia.trim()) {
        tancaParagraf();
        tancaLlista();
      } else {
        tancaLlista();
        paragraf.push(linia);
      }
    }
    tancaParagraf();
    tancaLlista();
    return html;
  }

  /* ---------- el DOM ---------- */

  function crea() {
    const arrel = document.createElement('div');
    arrel.className = 'xatia';
    arrel.innerHTML = `
      <button type="button" class="xatia-boto" aria-label="Obre ${escapa(op.titol)}" aria-expanded="false" aria-controls="xatia-plafo">
        ${icona('sparkles', 20)}<span>${escapa(op.titol)}</span>
      </button>
      <div class="xatia-fons" hidden></div>
      <aside id="xatia-plafo" class="xatia-plafo" aria-label="${escapa(op.titol)}" aria-hidden="true" inert>
        <header tabindex="-1" class="xatia-cap">
          <span class="xatia-titol">${icona('sparkles', 18)} ${escapa(op.titol)}</span>
          <button type="button" class="xatia-icona" data-fa="nova" aria-label="Conversa nova" title="Conversa nova">${icona('nova', 16)}</button>
          <button type="button" class="xatia-icona xatia-nomes-ordinador" data-fa="gran" aria-label="Fes-ho gran" title="Fes-ho gran">${icona('gran', 16)}</button>
          <button type="button" class="xatia-icona" data-fa="tanca" aria-label="Tanca" title="Tanca (Esc)">${icona('x', 18)}</button>
        </header>
        <div class="xatia-cos">
          <div class="xatia-columna">
            <div class="xatia-missatge xatia-missatge--ia xatia-salutacio"></div>
            <div class="xatia-conversa" role="log" aria-live="polite" aria-relevant="additions text" aria-busy="false"></div>
            <div class="xatia-final"></div>
          </div>
        </div>
        <footer class="xatia-peu">
          <div class="xatia-columna">
            <p class="xatia-error" role="alert" hidden></p>
            <p class="xatia-veu" hidden></p>
            <div class="xatia-preguntes"></div>
            <div class="xatia-preparades"></div>
            <p class="xatia-ajuda" hidden></p>
            <div class="xatia-entrada">
              <input type="file" accept="image/*" multiple hidden>
              <button type="button" class="xatia-icona" data-fa="captura" aria-label="Afegeix una captura" title="Afegeix una captura (també pots enganxar-la o arrossegar-la)">${icona('imatge', 18)}</button>
              <textarea rows="2" placeholder="Pregunta el que vulguis…"></textarea>
              <button type="button" class="xatia-icona xatia-icona--ple" data-fa="envia" aria-label="Envia">${icona('envia', 18)}</button>
            </div>
          </div>
        </footer>
      </aside>
      <div class="xatia-lupa" hidden><img alt=""></div>`;
    document.body.appendChild(arrel);
    const q = (s) => arrel.querySelector(s);
    el = {
      arrel,
      boto: q('.xatia-boto'),
      fons: q('.xatia-fons'),
      plafo: q('.xatia-plafo'),
      cos: q('.xatia-cos'),
      salutacio: q('.xatia-salutacio'),
      conversa: q('.xatia-conversa'),
      final: q('.xatia-final'),
      error: q('.xatia-error'),
      veu: q('.xatia-veu'),
      preguntes: q('.xatia-preguntes'),
      preparades: q('.xatia-preparades'),
      ajuda: q('.xatia-ajuda'),
      fitxer: q('input[type=file]'),
      caixa: q('textarea'),
      nova: q('[data-fa=nova]'),
      gran: q('[data-fa=gran]'),
      captura: q('[data-fa=captura]'),
      envia: q('[data-fa=envia]'),
      lupa: q('.xatia-lupa'),
    };
    connecta();
  }

  // A l'ordinador, en mida normal, es pot treballar a la pàgina alhora.
  const esAcoblat = () => !esMobil() && !estat.gran;

  // Streamlit 1.67 posa el testid de plegar al contenidor i el de desplegar
  // al botó de la capçalera (fora del menú). Els aria-label són alternatives.
  const selectorPlegaMenu = '[data-testid="stSidebarCollapseButton"] button, button[data-testid="stSidebarCollapseButton"], [data-testid="stSidebar"] button[aria-label="Collapse sidebar"]';
  const selectorDesplegaMenu = 'button[data-testid="stExpandSidebarButton"], [data-testid="stExpandSidebarButton"] button, [data-testid="stSidebarCollapsedControl"] button, [data-testid="stHeader"] button[aria-label="Expand sidebar"]';
  let menuXatObert = false;
  let menuPlegatPelXat = false;
  let clicMenuDelXat = false;
  let menuManual = false;
  let observaMenu;

  function menuVisible(node) {
    if (!node) return false;
    const rect = node.getBoundingClientRect();
    const estil = window.getComputedStyle(node);
    // El menú plegat pot conservar amplada, però estar fora de la pantalla.
    return rect.width > 0 && rect.height > 0 && rect.right > 0 && rect.bottom > 0 &&
      rect.left < window.innerWidth && rect.top < window.innerHeight &&
      estil.display !== 'none' && estil.visibility !== 'hidden' && estil.visibility !== 'collapse';
  }

  function botoMenu(selector) {
    // Streamlit oculta el control fins al hover; .click() també funciona ocult.
    // La visibilitat que determina l'estat és la del menú, no la del botó.
    return Array.from(document.querySelectorAll(selector)).find((boto) => !boto.disabled);
  }

  function deixaObservarMenu() {
    if (observaMenu) observaMenu.disconnect();
    observaMenu = undefined;
  }

  function clicaMenu(boto) {
    clicMenuDelXat = true;
    try { boto.click(); }
    finally { clicMenuDelXat = false; }
  }

  function plegaMenuPelXat() {
    if (!estat.obert || !esAcoblat() || menuManual || menuPlegatPelXat) {
      deixaObservarMenu();
      return;
    }
    const menu = document.querySelector('[data-testid="stSidebar"]');
    if (!menu) return; // Pot muntar-se després del widget.
    if (!menuVisible(menu)) {
      deixaObservarMenu(); // Ja estava plegat: no ens correspon restaurar-lo.
      return;
    }
    // També a 1440 px: reservem lloc al plafó i almenys 1000 px a la pàgina.
    const ampladaMenu = menu.getBoundingClientRect().width;
    const ampladaPlafo = el.plafo.getBoundingClientRect().width;
    if (window.innerWidth - ampladaMenu - ampladaPlafo >= 1000) {
      deixaObservarMenu();
      return;
    }
    const boto = botoMenu(selectorPlegaMenu);
    if (!boto) return;
    deixaObservarMenu();
    menuPlegatPelXat = true;
    clicaMenu(boto);
  }

  function clicManualMenu(e) {
    if (!menuXatObert || clicMenuDelXat) return;
    if (e.target.closest && e.target.closest(selectorPlegaMenu + ', ' + selectorDesplegaMenu)) {
      menuPlegatPelXat = false;
      menuManual = true;
      deixaObservarMenu();
    }
  }

  function sincronitzaMenu() {
    if (typeof document.querySelector !== 'function') return;
    if (menuXatObert === estat.obert) {
      if (estat.obert) plegaMenuPelXat();
      return;
    }
    menuXatObert = estat.obert;
    deixaObservarMenu();
    if (estat.obert) {
      menuPlegatPelXat = false;
      menuManual = false;
      if (!esAcoblat()) return;
      // Només mentre esperem el muntatge inicial; mai replegar un menú manual.
      if (typeof MutationObserver !== 'undefined') {
        observaMenu = new MutationObserver(plegaMenuPelXat);
        observaMenu.observe(document.body, { childList: true, subtree: true, attributes: true });
      }
      plegaMenuPelXat();
    } else {
      const restaura = menuPlegatPelXat;
      menuPlegatPelXat = false;
      if (restaura && !esMobil() && !menuVisible(document.querySelector('[data-testid="stSidebar"]'))) {
        const boto = botoMenu(selectorDesplegaMenu);
        if (boto) clicaMenu(boto);
      }
    }
  }

  let midaPlafó;
  let resizePendent;
  function avisaAmplada() {
    // El navegador aplica primer l'amplada nova. Plotly i la graella tornen
    // a mesurar el seu contenidor; no cal canviar la mida real de la finestra.
    window.dispatchEvent(new Event('resize'));
  }

  function mostraFinal() {
    if (estat.obert) el.final.scrollIntoView({ block: 'end' });
  }

  function sincronitzaPlafó() {
    sincronitzaMenu();
    const acoblat = estat.obert && esAcoblat();
    document.documentElement.classList.toggle('xatia-obert', acoblat);
    el.fons.hidden = !estat.obert || acoblat;
    const mida = `${estat.obert}:${estat.gran}:${esMobil()}`;
    if (mida !== midaPlafó) {
      midaPlafó = mida;
      window.clearTimeout(resizePendent);
      avisaAmplada();
      // Respatller per a transicions interrompudes i moviment reduït (sense
      // transitionend). No es programa en cada tros de resposta ni pantalla.
      resizePendent = window.setTimeout(() => { avisaAmplada(); mostraFinal(); }, 260);
    }
  }

  function acabaTransicio(e) {
    if ((e.target === el.plafo && ['width', 'transform'].includes(e.propertyName)) ||
        (e.target.matches?.('.stApp') && e.propertyName === 'width')) {
      window.clearTimeout(resizePendent);
      avisaAmplada();
      mostraFinal();
    }
  }

  function clicFons() {
    if (!esAcoblat()) tanca();
  }

  function teclaPlafó(e) {
    if (e.key !== 'Escape') return;
    if (!el.lupa.hidden) el.lupa.hidden = true;
    else if (estat.obert && (!esAcoblat() || el.plafo.contains(document.activeElement))) tanca();
  }

  function connecta() {
    // Captura abans dels handlers de React; els clics del xat queden exclosos.
    document.addEventListener('click', clicManualMenu, true);
    el.boto.addEventListener('click', () => obre());
    el.fons.addEventListener('click', clicFons);
    el.plafo.addEventListener('click', (e) => {
      const fa = e.target.closest('[data-fa]');
      if (fa) {
        const accio = fa.dataset.fa;
        if (accio === 'tanca') tanca();
        else if (accio === 'gran') posaGran(!estat.gran);
        else if (accio === 'nova') conversaNova();
        else if (accio === 'captura') el.fitxer.click();
        else if (accio === 'envia') envia(el.caixa.value, true);
        else if (accio === 'copia-ids') copiaIds(fa);
        else if (accio === 'treu') {
          estat.preparades = estat.preparades.filter((_, i) => i !== Number(fa.dataset.i));
          pinta();
        } else if (accio === 'pregunta') {
          envia(fa.dataset.text, false);
          enfocaEntrada();
        }
        return;
      }
      const img = e.target.closest('.xatia-captures img, .xatia-preparada img');
      if (img) mostraGran(img.src);
    });
    el.fitxer.addEventListener('change', () => {
      if (el.fitxer.files.length) afegeixCaptures(el.fitxer.files);
      el.fitxer.value = '';
    });
    el.caixa.addEventListener('input', creixCaixa);
    el.caixa.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        envia(el.caixa.value, true);
      }
    });
    /* Una captura enganxada (Cmd+V) a qualsevol lloc del plafó. */
    el.plafo.addEventListener('paste', (e) => {
      const fitxers = [...(e.clipboardData ? e.clipboardData.files : [])].filter((f) => f.type.startsWith('image/'));
      if (fitxers.length) {
        e.preventDefault();
        afegeixCaptures(fitxers);
      }
    });
    /* Arrossegar captures a sobre del plafó. */
    let dins = 0;
    const ambFitxers = (e) => e.dataTransfer && [...e.dataTransfer.types].includes('Files');
    el.plafo.addEventListener('dragenter', (e) => {
      if (!ambFitxers(e)) return;
      e.preventDefault();
      dins++;
      el.plafo.classList.add('xatia-plafo--deixant');
    });
    el.plafo.addEventListener('dragover', (e) => {
      if (!ambFitxers(e)) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });
    el.plafo.addEventListener('dragleave', () => {
      dins = Math.max(0, dins - 1);
      if (!dins) el.plafo.classList.remove('xatia-plafo--deixant');
    });
    el.plafo.addEventListener('drop', (e) => {
      if (!ambFitxers(e)) return;
      e.preventDefault();
      dins = 0;
      el.plafo.classList.remove('xatia-plafo--deixant');
      afegeixCaptures(e.dataTransfer.files);
    });
    el.lupa.addEventListener('click', () => (el.lupa.hidden = true));
    document.addEventListener('transitionend', acabaTransicio);
    window.addEventListener('keydown', teclaPlafó);
    /* Al mòbil, el teclat tapa la caixa: el plafó s'acaba on comença el teclat. */
    if (window.visualViewport) {
      const teclat = () => {
        const tapat = Math.max(0, window.innerHeight - visualViewport.height - visualViewport.offsetTop);
        el.arrel.style.setProperty('--xatia-teclat', `${tapat}px`);
      };
      visualViewport.addEventListener('resize', teclat);
      visualViewport.addEventListener('scroll', teclat);
    }
    window.matchMedia('(max-width: 699px)').addEventListener('change', pinta);
    window.addEventListener('resize', sincronitzaMenu);
  }

  function creixCaixa() {
    const c = el.caixa;
    c.style.height = '';
    if (c.value && c.scrollHeight > c.clientHeight) c.style.height = `${Math.min(c.scrollHeight + c.offsetHeight - c.clientHeight, 180)}px`;
  }

  function mostraGran(src) {
    el.lupa.querySelector('img').src = src;
    el.lupa.hidden = false;
  }

  /* ---------- pintar ---------- */

  const NOMS_EINES = {
    horari_grup: 'Horari del grup', aules_lliures: 'Aules lliures',
    ocupacio_aula: 'Ocupació de l’aula', xifra: 'Xifra de l’horari',
    resultat_proposta: 'Resultat de la proposta', consulta_sql: 'Consulta de l’horari',
    prova_canvi: 'Prova d’un canvi',
  };
  const ETIQUETES_ARGS = {
    titulacio: 'titulació', curs: 'curs', grup: 'grup', dia: 'dia', data: 'data',
    hora_ini: 'hora', h_ini: 'hora', h_fi: 'hora final', durada_min: 'durada',
    places_min: 'places', tipus: 'tipus', setmana: 'setmana', aula: 'aula',
    id: 'xifra', apartat: 'horari proposat', proposta: 'horari', sql: 'consulta',
    canvi: 'canvi', id_sessio: 'sessió', activitat_id: 'activitat',
    aules_tancades: 'aules tancades', grups_creixen: 'grups que creixen',
    sessions_cancel_lades: 'sessions cancel·lades', data_ini: 'data inicial',
    data_fi: 'data final', alumnes: 'alumnes', codi: 'codi d’assignatura',
    recuperar_fins: 'recuperar fins al',
  };

  function descriuArgument(clau, valor) {
    const etiqueta = ETIQUETES_ARGS[clau] || clau.replace(/_/g, ' ');
    if (Array.isArray(valor)) return `${etiqueta}: ${valor.map(descriuValor).join('; ')}`;
    if (valor && typeof valor === 'object') return `${etiqueta}: ${descriuValor(valor)}`;
    if (clau === 'proposta') return ['avui', 'partida'].includes(valor)
      ? 'horari d’avui' : `horari proposat: ${valor}`;
    if (clau === 'dia') valor = ({L: 'dilluns', M: 'dimarts', X: 'dimecres', J: 'dijous', V: 'divendres'})[valor] || valor;
    if (clau === 'durada_min') valor = `${valor} min`;
    if (clau === 'places_min') valor = `${valor} places o més`;
    if (clau === 'tipus') valor = ({moure: 'moure una classe', imprevist: 'imprevist'})[valor] || valor;
    return `${etiqueta}: ${valor}`;
  }

  function descriuValor(valor) {
    if (valor && typeof valor === 'object') return Object.entries(valor)
      .filter(([, v]) => v !== null && v !== undefined)
      .map(([k, v]) => descriuArgument(k, v)).join(' · ');
    return String(valor);
  }

  function htmlConsultes(consultes) {
    const correctes = Array.isArray(consultes)
      ? consultes.filter((c) => c && c.ok === true && !c.error) : [];
    if (!correctes.length) return '';
    return '<details class="xatia-consultes"><summary>Comprova-ho</summary>' + correctes.map((c) => {
      const args = c.args && typeof c.args === 'object' ? c.args : {};
      const descripcio = [NOMS_EINES[c.eina] || String(c.eina || 'Consulta'),
        ...Object.entries(args).filter(([, v]) => v !== null && v !== undefined)
          .map(([k, v]) => descriuArgument(k, v))].join(' · ');
      const ids = Array.isArray(c.id_sessio) ? c.id_sessio.filter((id) => typeof id === 'string' && id).slice(0, 10) : [];
      const mes = Math.max(0, (Number(c.total_id) || 0) - ids.length);
      const sessions = ids.length ? `<div class="xatia-consulta-ids"><span>id_sessio: <code>${escapa(ids.join(', '))}</code>${mes ? ` · +${mes} més` : ''}</span><button type="button" data-fa="copia-ids" data-ids="${escapa(ids.join(','))}" aria-label="Copia els identificadors de sessió">Copia</button><span role="status" class="xatia-consulta-estat"></span></div>` : '';
      const aules = c.eina === 'aules_lliures' && Array.isArray(c.resultat?.files)
        ? c.resultat.files.filter((fila) => typeof fila?.aula === 'string').slice(0, 25)
          .map((fila) => fila.aula) : [];
      const llistaAules = aules.length
        ? `<p>Aules: <code>${escapa(aules.join(', '))}</code></p>` : '';
      const consulta = c.consulta ? `<pre><code>${escapa(String(c.consulta))}</code></pre>` : '';
      return `<section class="xatia-consulta"><p>${escapa(descripcio)}</p>${sessions}${llistaAules}${consulta}</section>`;
    }).join('') + '</details>';
  }

  async function copiaIds(boto) {
    const estatCopia = boto.parentElement.querySelector('[role="status"]');
    try {
      await navigator.clipboard.writeText(boto.dataset.ids);
      estatCopia.textContent = 'Copiat';
      return;
    } catch (e) {
      /* Alguns navegadors bloquegen el porta-retalls modern. */
    }
    const focusAnterior = document.activeElement;
    const temporal = document.createElement('textarea');
    temporal.value = boto.dataset.ids;
    temporal.setAttribute('readonly', '');
    temporal.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0;';
    let copiat = false;
    try {
      document.body.appendChild(temporal);
      temporal.select();
      copiat = document.execCommand('copy');
    } catch (e) {
      /* Encara es pot copiar manualment la selecció visible. */
    } finally {
      temporal.remove();
      if (focusAnterior && focusAnterior.focus) focusAnterior.focus();
    }
    if (copiat) {
      estatCopia.textContent = 'Copiat';
      return;
    }
    const rang = document.createRange();
    rang.selectNodeContents(boto.parentElement.querySelector('code'));
    const seleccio = window.getSelection();
    seleccio.removeAllRanges();
    seleccio.addRange(rang);
    estatCopia.textContent = 'Seleccionat: prem Cmd+C o Ctrl+C per copiar-ho';
  }

  function htmlMissatge(m) {
    if (m.role === 'user') {
      const captures = m.imatges && m.imatges.length
        ? `<span class="xatia-captures">${m.imatges.map((u) => `<img src="${u}" alt="Captura">`).join('')}</span>`
        : m.fotos ? `<span class="xatia-nota">${m.fotos === 1 ? 'amb una captura' : `amb ${m.fotos} captures`}</span>` : '';
      return `<div class="xatia-missatge xatia-missatge--jo">${captures}${escapa(m.content)}</div>`;
    }
    return `<div class="xatia-missatge xatia-missatge--ia">${markdown(m.content)}${htmlConsultes(m.consultes)}</div>`;
  }

  function pintaConversa() {
    let html = estat.missatges.map(htmlMissatge).join('');
    if (estat.feina) {
      if (estat.parcial) html += `<div class="xatia-missatge xatia-missatge--ia xatia-escrivint">${markdown(estat.parcial)}</div>`;
      if (estat.estatResposta || estat.eina || !estat.parcial) html += `<div class="xatia-missatge xatia-missatge--ia xatia-pensant">${estat.estatResposta || (estat.eina ? 'Consultant l’horari…' : 'Pensant…')}</div>`;
    }
    // Anunciem la resposta completa, sense llegir cada fragment del flux.
    el.conversa.setAttribute('aria-busy', String(estat.feina));
    if (el.conversa.xatiaHtml === html) return;
    const segueix = !el.cos || el.cos.scrollHeight - el.cos.scrollTop - el.cos.clientHeight < 80;
    const posicio = el.cos && el.cos.scrollTop;
    el.conversa.innerHTML = html;
    el.conversa.xatiaHtml = html;
    if (segueix) el.final.scrollIntoView({ block: 'end' });
    else el.cos.scrollTop = posicio;
  }

  function preguntesAra() {
    if (estat.missatges.some((m) => m.role === 'assistant')) return ['Com ho saps?'];
    const p = estat.pantalla;
    if (p && Array.isArray(p.preguntes)) return p.preguntes;
    return typeof op.preguntes === 'function' ? op.preguntes(p) || [] : op.preguntes || [];
  }

  function pinta() {
    if (!el.arrel) return;
    const { obert, gran, feina } = estat;
    const ocupat = feina || estat.preparant > 0;
    el.arrel.classList.toggle('xatia--obert', obert);
    el.arrel.classList.toggle('xatia--gran', gran && !esMobil());
    el.arrel.classList.toggle('xatia--amb-conversa', estat.missatges.length > 0);
    el.boto.hidden = obert;
    el.boto.setAttribute('aria-expanded', String(obert));
    sincronitzaPlafó();
    el.plafo.setAttribute('aria-hidden', String(!obert));
    el.plafo.inert = !obert;
    el.gran.innerHTML = icona(gran ? 'petit' : 'gran', 16);
    el.gran.setAttribute('aria-label', gran ? 'Torna-ho petit' : 'Fes-ho gran');
    el.gran.title = gran ? 'Torna-ho petit' : 'Fes-ho gran';
    el.nova.hidden = !estat.missatges.length;
    el.nova.disabled = feina;

    el.salutacio.textContent = op.salutacio + (estat.llesta ? '' : ' (Ara mateix la IA no està a punt.)');
    el.salutacio.hidden = estat.missatges.length > 0;
    pintaConversa();

    el.error.hidden = !estat.error;
    el.error.textContent = estat.error;
    pintaPeu();
    el.preparades.innerHTML = estat.preparades
      .map((u, i) => `<span class="xatia-preparada"><img src="${u}" alt="Captura ${i + 1}"><button type="button" data-fa="treu" data-i="${i}" aria-label="Treu la captura">${icona('x', 12)}</button></span>`)
      .join('');
    const ajuda = estat.preparant ? 'Preparant la captura…' : estat.avis;
    el.ajuda.hidden = !ajuda;
    el.ajuda.textContent = ajuda;

    el.captura.disabled = feina || estat.preparades.length >= op.maxCaptures;
    el.envia.disabled = ocupat || (!el.caixa.value.trim() && !estat.preparades.length);
    el.caixa.placeholder = estat.preparades.length ? 'Què en vols saber?' : esMobil() ? 'Pregunta…' : 'Pregunta el que vulguis, o passa’m una captura…';
  }

  function pintaPeu() {
    if (!el.veu) return;
    const ocupat = estat.feina || estat.preparant > 0;
    /* Què veu de la pantalla, perquè se sàpiga que se li pot dir «i això?». */
    const veu = estat.pantalla && estat.pantalla.resum;
    el.veu.hidden = !veu;
    el.veu.textContent = veu ? `Context: ${veu}` : '';
    el.veu.title = veu || '';

    el.preguntes.innerHTML = preguntesAra()
      .map((t) => `<button type="button" class="xatia-fitxa" data-fa="pregunta" data-text="${escapa(t)}"${ocupat ? ' disabled' : ''}>${escapa(t)}</button>`)
      .join('');
  }

  function enfocaEntrada() {
    (esMobil() ? el.plafo.querySelector('header') : el.caixa).focus({ preventScroll: true });
  }

  /* ---------- accions ---------- */

  function obre(pregunta) {
    estat.obert = true;
    pinta();
    if (pregunta) envia(pregunta, false);
    /* Al mòbil no: obriria el teclat i taparia la conversa. */
    else if (!esMobil()) setTimeout(() => el.caixa.focus(), 230);
  }

  function tanca() {
    estat.obert = false;
    pinta();
    el.boto.focus({ preventScroll: true });
  }

  function posaGran(si) {
    estat.gran = si;
    try {
      localStorage.setItem(op.clauMemoria + '.gran', si ? '1' : '0');
    } catch (e) {
      /* no es recordarà */
    }
    pinta();
  }

  function conversaNova() {
    if (estat.feina) return;
    estat.missatges = [];
    estat.contextInicial = undefined;
    estat.error = '';
    desa();
    pinta();
    enfocaEntrada();
  }

  let salutActual = 0;
  async function miraSalut() {
    const peticio = ++salutActual;
    let llesta;
    try {
      const r = await fetch(op.api, { signal: AbortSignal.timeout(8000) });
      const dades = await r.json();
      llesta = !!(dades && dades.teClau);
    } catch (e) {
      llesta = false;
    }
    if (peticio !== salutActual) return;
    estat.llesta = llesta;
    pinta();
  }

  window.XatIA = {
    inicia(opcions = {}) {
      if (op) return;
      op = { ...PER_DEFECTE, ...opcions };
      llegeixMemoria();
      crea();
      el.caixa.addEventListener('input', () => {
        el.envia.disabled = estat.feina || estat.preparant > 0 || (!el.caixa.value.trim() && !estat.preparades.length);
      });
      pinta();
      miraSalut();
    },
    api(url) {
      if (!op) return;
      op.api = url;
      return miraSalut();
    },
    pantalla(p) {
      estat.pantalla = p || null;
      pintaPeu();
    },
    obre,
    tanca,
    conversaNova,
  };
})();

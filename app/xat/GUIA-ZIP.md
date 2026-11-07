# Guia: posar el xat amb la IA en un programa en Python

Passa aquest fitxer (i la carpeta sencera) a la IA que treballi a l'altre programa (Claude Code,
Codex…) amb una frase com: «Llegeix GUIA-PER-A-LA-IA.md i posa aquest xat al nostre programa».

El xat és el de l'estilista d'Armari, tret de tot el que és de roba. Els fitxers ja funcionen
tal qual: `servidor/app_exemple.py` és un programa de mostra amb el xat posat.

## Què fa

- **Botó baix a la dreta** amb la icona ✦ i el nom («Assistent»). Al mòbil, només la icona.
- **S'obre a la dreta** com un plafó de 420 px. A l'ordinador no enfosqueix la pàgina; al mòbil
  ocupa tota la pantalla. Es tanca amb la creu, amb Esc o tocant fora.
- **Es pot fer gran** (botó ⤢ de la capçalera): ocupa tota la finestra, amb la conversa en una
  columna llegible al mig. Es recorda. Al mòbil no hi és, perquè ja és gran.
- **Preguntes proposades** a sobre de la caixa. Canvien segons la pantalla del programa. Un toc
  la pregunta directament, sense tocar el que hi hagi escrit a la caixa.
- **Captures de pantalla**: botó de la imatge, enganxar (Cmd+V / Ctrl+V) o arrossegar-les a
  sobre del plafó. Com a molt 3 per pregunta. Es redueixen al navegador (JPEG, costat llarg de
  1600 px) abans d'enviar: es llegeix el text i pesen poc. Es poden treure abans d'enviar i
  ampliar-les fent-hi clic. Només imatges: res d'altres fitxers.
- **Veu la pantalla**: el programa diu què hi ha obert amb `XatIA.pantalla({...})`. A sobre de
  la caixa surt «Veu: …», i el text va a la IA davant de cada pregunta, dins `<pantalla>`.
- **Resposta en directe**: surt mentre s'escriu; abans, «Pensant…».
- **Errors**: si falla, la pregunta desapareix de la conversa i el text i les captures tornen a
  la caixa per tornar-ho a enviar. L'error surt a tocar de la caixa.
- **Memòria**: la conversa es recorda en aquest navegador (localStorage), sense les captures (en
  queda «amb una captura»). Botó ↺ «Conversa nova».
- **Servidor**: la clau de la IA és només al servidor. Les instruccions fixes (què és el
  programa, com ha de respondre) són a `servidor/instruccions.md`. IA de reserva opcional.
- **No hi ha** comptador d'euros (Armari en té; aquí no es volia).

## Fitxers

```
servidor/
  xat_ia.py          el cor: valida la conversa, parla amb la IA, fa el flux. Sense framework.
  xat_flask.py       adaptador Flask (Blueprint amb GET i POST /api/xat)
  app_exemple.py     programa de mostra (Flask) que serveix web/ i el xat
  instruccions.md    les instruccions fixes de la IA (el «system prompt»): CANVIA-LES
  .env.exemple       on van l'adreça, la clau i el model de la IA
  requirements.txt   flask
web/
  xat-ia.js          el xat (JavaScript sense framework); crea el botó i el plafó
  xat-ia.css         els estils, tots amb prefix .xatia i colors en variables --xatia-*
  exemple.html       pàgina de mostra amb dues «pantalles» que canvien el que veu el xat
captures/            com es veu
```

## Provar-ho primer, sense IA

```bash
cd servidor
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
IA_PROVA=1 python app_exemple.py
```

Obre http://localhost:5050. Amb `IA_PROVA=1` respon un text inventat que diu què ha rebut
(la pregunta, quantes captures, la pantalla): serveix per comprovar-ho tot sense gastar res.

## Posar-lo al programa

### 1. El servidor

**Flask:**

```python
from xat_flask import xat_ia   # copia xat_ia.py, xat_flask.py i instruccions.md al projecte
app.register_blueprint(xat_ia)
```

Amb `threaded=True` (o gunicorn amb diversos fils/workers): mentre una resposta s'escriu, el
servidor n'ha d'atendre d'altres.

**FastAPI** (les mateixes crides a `xat_ia.py`):

```python
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import xat_ia as nucli

nucli.carrega_env()
app = FastAPI()

@app.get("/api/xat")
def salut():
    return nucli.salut()

@app.post("/api/xat")
async def pregunta(request: Request):
    cru = await request.body()
    if len(cru) > nucli.MAX_COS:
        return JSONResponse({"error": "La conversa és massa llarga. Comença’n una de nova."}, 413)
    if nucli.falta():
        return JSONResponse({"error": "La IA encara no està a punt."}, 503)
    try:
        esdeveniments = nucli.flux(nucli.valida(json.loads(cru or b"null")))
    except ValueError:
        return JSONResponse({"error": "La petició no és JSON."}, 400)
    except nucli.ErrorXat as e:
        return JSONResponse({"error": e.missatge}, e.estat)
    # flux() és síncron (urllib): StreamingResponse el passa a un fil sol.
    return StreamingResponse(esdeveniments, media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
```

**Django**: el mateix amb `JsonResponse` i `StreamingHttpResponse(esdeveniments,
content_type="text/event-stream")`, i `@csrf_exempt` o el token CSRF a la capçalera del fetch.

**Si el programa té usuaris**: a la ruta POST, comprova que n'hi ha un d'entrat abans de cridar
la IA (hi ha el lloc marcat a `xat_flask.py`). La IA costa diners.

**Darrere de nginx**: la capçalera `X-Accel-Buffering: no` ja hi va; si no, la resposta
arribaria tota de cop al final.

### 2. La IA (Quiver o la que sigui)

Copia `.env.exemple` com a `.env` i omple `IA_URL`, `IA_CLAU` i `IA_MODEL`. `xat_ia.py` parla el
format **OpenAI-compatible** (`POST {IA_URL}/chat/completions` amb `stream: true`, captures com a
`image_url` amb data URI), que és el que fan servir OpenAI, OpenRouter, Mistral, Groq, Ollama…

**Atenció amb Quiver:** el Quiver que es troba a internet (QuiverAI, `api.quiver.ai`) és un model
que fa gràfics SVG, no un model de xat. Abans de res, comprova a la documentació de la IA que
feu servir:

1. Que té un model de xat que **accepti imatges** (per veure les captures).
2. Quin format té l'API. Si és OpenAI-compatible, només cal el `.env`. Si no, canvia
   **només** `_trossos_api()` a `xat_ia.py`: ha de donar `("tros", text)` mentre escriu i
   `("fi", {"tallada": bool, "model": str})` al final, i llençar `ErrorIA` si falla. La resta no
   canvia.
3. Si no té flux en directe: fes una crida normal a `_trossos_api()` i dona tot el text en un sol
   `("tros", text)`. El xat ho mostra igual, només que de cop.

La clau **mai** al JavaScript ni al repositori: al `.env` (que va al `.gitignore`) o a les
variables d'entorn del servidor.

### 3. El navegador

A totes les pàgines del programa (a la plantilla base):

```html
<link rel="stylesheet" href="/static/xat-ia.css">
<script src="/static/xat-ia.js"></script>
<script>
  XatIA.inicia({
    api: '/api/xat',
    titol: 'Assistent',
    salutacio: 'Hola! Pregunta’m el que vulguis…',
    preguntes: ['Què puc fer aquí?'],            // o una funció (pantalla) => [...]
    // context: () => 'Dades fixes per al primer missatge (opcional)',
  });
</script>
```

Opcions: `api`, `titol`, `salutacio`, `preguntes`, `context`, `clauMemoria` (si hi ha diversos
usuaris al mateix navegador, posa-hi l'id de l'usuari: `'xat-ia.' + idUsuari`), `maxCaptures`
(3), `midaCaptura` (1600).

### 4. Que vegi la pantalla

Cada cop que canvia el que es veu (una pàgina, una fitxa oberta, un filtre):

```js
XatIA.pantalla({
  resum: 'Factura 123',                                  // curt: surt a «Veu: …»
  text: 'Està mirant la factura 123 de Joan Puig, 450 €, pendent de cobrar.',  // va a la IA
  preguntes: ['Per què està pendent?', 'Com l’envio?'],  // opcional: les d'aquesta pantalla
});
XatIA.pantalla(null);   // res de particular
```

El `text` ha de ser el que una persona diria si li ensenyés la pantalla: les dades que es veuen,
no l'HTML. Curt (unes línies). No hi posis res que la persona no pugui veure.

Altres crides: `XatIA.obre('pregunta')` (obre i pregunta, per exemple des d'un botó «Pregunta-ho a
l'assistent» d'una pantalla), `XatIA.obre()`, `XatIA.tanca()`, `XatIA.conversaNova()`.

### 5. Els colors

`xat-ia.css` porta un tema clar i un de fosc (segueix el sistema; amb
`<html data-theme="light|dark">` mana el programa). Per posar-hi els colors del programa:

```css
:root { --xatia-accent: #0b6bcb; --xatia-sobre-accent: #fff; }
```

## El contracte entre el navegador i el servidor

**GET /api/xat** → `{"ok": true, "teClau": true, "model": "…", "falta": null}`. El xat ho mira en
carregar; si `teClau` és fals, ho diu a la salutació i no envia.

**POST /api/xat** amb `{"missatges": [...]}`:

- Alternen `user` / `assistant`, comencen i acaben amb `user`. Com a molt 60.
- Un missatge de text: `{"role": "user", "content": "<pantalla>\n…\n</pantalla>\n\nla pregunta"}`.
- L'última pregunta amb captures: `content` és una llista
  `[{"type":"text","text":"…"}, {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,…"}}]`.
- Les preguntes d'abans que portaven captures van només amb text i la nota
  «[Amb una captura, que ja has vist.]»: tornar-les a enviar es pagaria a cada pregunta.
- Al primer missatge, si hi ha `context`, va davant dins `<context>…</context>`.

Resposta:

- Si falla abans de començar: JSON `{"error": "…"}` amb codi 400/413/502/503. El xat mostra
  l'error tal qual, o sigui que els textos han de ser per a la persona.
- Si va bé: `text/event-stream` amb `data: {"tros": "…"}` …, i al final
  `data: {"fi": true, "tallada": false, "model": "…"}`. Si es talla a mig camí:
  `data: {"error": "…"}`.

## Per què és així (el que es va aprendre a Armari)

- Les instruccions van al servidor i el context al primer missatge: les instruccions queden
  idèntiques d'una conversa a l'altra i l'API les pot reaprofitar de la memòria cau (més barat).
- El servidor refà cada missatge camp a camp i només accepta data URI d'imatge: el navegador no
  pot colar-hi instruccions, adreces externes ni camps estranys.
- La conversa es desa sense les captures perquè no caben a localStorage (uns 5 MB).
- La resposta es pinta com a molt 20 cops per segon: pintar-la a cada tros alentia la pàgina.
- Una pregunta proposada no esborra el que hi hagi escrit a la caixa.
- Al mòbil, obrir el xat no enfoca la caixa (el teclat taparia la conversa), la caixa fa 16 px
  (l'iPhone no fa zoom) i el plafó s'acaba on comença el teclat.
- Al mòbil, amb conversa, les preguntes proposades van en una sola línia que llisca, perquè es
  llegeixi la resposta.
- El text de la IA es mostra amb un markdown petit (negreta, llistes, enllaços) que escapa tot
  l'HTML: la resposta no pot injectar res a la pàgina.

## Comprovar que està ben posat

1. El botó surt baix a la dreta a totes les pàgines, i no tapa res important.
2. S'obre a la dreta, es fa gran i torna petit, i es tanca amb Esc.
3. Les preguntes proposades canvien en canviar de pantalla, i «Veu: …» diu la pantalla.
4. Una captura enganxada amb Cmd+V surt a sobre de la caixa, i la IA la descriu bé.
5. La resposta surt a poc a poc.
6. Amb el servidor aturat, enviar dona un error i el text torna a la caixa.
7. En recarregar, la conversa hi és; «Conversa nova» la buida.
8. Al mòbil (375 px) ocupa tota la pantalla i el teclat no tapa la caixa.
9. En tema clar i en fosc es llegeix tot.
10. La clau no surt enlloc del navegador (pestanya Xarxa).

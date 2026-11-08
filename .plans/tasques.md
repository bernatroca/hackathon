# Tasques de la part 2 · Proposta d'horari

> **Estat.** L'equip va donar l'OK el ds 7-11 a la tarda. Fase 0 feta.
> Orquestra i integra la sessió de Claude de la part 2. La sessió «Part 1» no llança subagents de la part 2.
> Especificació: `.plans/nivell2-horari-spec.md`.

## Com ens repartim

- **Com a màxim, 4 subagents de Codex alhora.** El Mac té 10 nuclis, i cada solver CP-SAT corre amb 2 fils (`num_workers = 2`). El temps per execució del solver és de 300 s, si la tasca no en diu un altre.
- **Un worktree per tasca**, mai per rol. Cada worktree surt de `main` en el moment de llançar la tasca: `git worktree add ../hack-n2-<títol> -b n2-<títol>`. El títol és el de la taula de cada fase (`backend-1`, `dades-1`…).
- **Dues tasques no toquen mai el mateix fitxer.** Cada tasca té una llista tancada de fitxers que pot crear o modificar.
- **Fitxers compartits, només de la integració:** `nivell2/__init__.py`, `nivell2/base.py`, `requirements.txt`, `app/app.py` (llevat que una tasca ho digui), `.plans/`, `docs/` i `.gitignore`.
- **Integració** (Claude, aquesta sessió): crea els worktrees, executa l'ordre de «fet», fa els commits a la branca de la tasca, uneix la branca a `main` i porta `main` als worktrees que en depenen.

## Què veu cada subagent

Codex no ha vist la conversa. Només sap el que hi ha al prompt i al seu worktree. Per això:

1. L'especificació i aquest fitxer han de ser a `main`, amb un commit, **abans** de crear el worktree. Si no, el subagent llegeix una versió vella.
2. El prompt és autosuficient: la persona, la tasca, els fitxers permesos, l'ordre de «fet» i la regla de preguntes (plantilla de la skill `subagents-codex`).
3. **Dades:** a `/Users/bernatroca/Bernat/Hackathon/repte/repte-horaris-escola/`, en només lectura, amb la ruta absoluta. El verificador s'executa des d'aquella carpeta.
4. **Python:** el worktree no té `.venv`. Sempre `/Users/bernatroca/Bernat/Hackathon/.venv/bin/python`, que ja té `ortools` 9.15.
5. Sense xarxa (`network: none`) i sense commits. Model `gpt-6.1-sol`, effort `medium`; `high` només si torna BLOCKED.

## Fase 0 · Integració (abans de llançar res)

| # | Què | Fet quan |
|---|---|---|
| 0.1 | Restaurar l'especificació. El commit `abe83e1` la va tallar de 233 a 50 línies: es recupera la versió `51b718a` i s'hi tornen a posar les 5 línies bones d'`abe83e1`. | `wc -l` ≥ 230 i hi ha l'apartat «Contracte de lliurament» |
| 0.2 | Posar a l'especificació la prioritat (la rutina primer), els pesos, un glossari i els casos especials (apartat «Detalls per programar»). | L'equip ho ha llegit i dona l'OK |
| 0.3 | Esquelet comú `nivell2/base.py`: carregar el paquet (amb els alumnes de `dades/alumnes_sense_dada.json` als grups sense dada), el tipus `Proposta`, escriure el CSV, cridar `avalua` i llegir el veredicte del JSON. Tots el fan servir. | `python -c "import nivell2.base"` va bé |
| 0.4 | Treure els worktrees antics de la part 1 (`hack-dades1`…`4`, `hack-frontend`), que ja són a `main`. | `git worktree list` només mostra `main` |

## Fase 1 · 4 subagents en paral·lel

| Títol | Rol | Tasca | Fitxers permesos | Fet quan |
|---|---|---|---|---|
| `backend-1` | Backend | **5.1 Aules.** Assignador d'aules genèric: rep el dia i l'hora de cada sessió i en tria l'aula (tipus, aforament, R4-AULA, reserva R8 per franja d'una hora, aula base, pocs canvis). El 5.2 el fa servir després. | `nivell2/aules.py`, `nivell2/s51.py`, `nivell2/test_aules.py`, `resultats/nivell2/5.1/` | `python -m nivell2.s51` escriu la proposta, i `python -m horaris check … --semestre 2 --nomes-aules --json` diu VALIDA |
| `backend-2` | Backend | **5.2 Franges.** Model CP-SAT del dia i l'hora per activitat dins el seu torn: calendari per data real, docent i alumnat sense solapaments, PLAB com a obstacles, compartides juntes, capacitat per franja i mida d'aula, i mínims canvis. Encara sense aules. | `nivell2/franges.py`, `nivell2/test_franges.py` | El test dona 0 sessions fora de torn i 0 solapaments nous de docent i d'alumnat, i escriu l'estat del solver |
| `dades-1` | Dades | **Xifres.** La taula abans i després de l'especificació: veredicte, rutina, canvis de torn, aules per grup i setmana, objectius del verificador i percentatge per titulació. | `nivell2/comprova.py`, `nivell2/xifres.py`, `nivell2/test_xifres.py` | `python -m nivell2.comprova <proposta_partida.csv>` treu la taula, i els números del verificador quadren amb el JSON |
| `frontend-1` | Frontend | **Graella.** La pàgina «Part 2» amb el disseny B1: la vista per grup (avui i proposta costat per costat) i la vista per aula. Al principi, amb dades de mostra (la partida). | `app/pagines/part2.py`, `app/components/graella.py`, `app/test_part2.py`, i la línia que afegeix la pàgina a `app/app.py` | `pytest app/test_part2.py` passa i l'app obre la pàgina sense errors |

## Fase 2 · Quan la fase 1 és a `main`

| Títol | Rol | Tasca | Fitxers permesos | Fet quan |
|---|---|---|---|---|
| `backend-2` (mateix fil) | Backend | **5.2 sencer.** Les franges més l'assignador d'aules de `backend-1`. Primer VALIDA, i després millorar amb un límit de temps. | `nivell2/franges.py`, `nivell2/s52.py`, `resultats/nivell2/5.2/` | `python -m horaris check … --semestre 2 --json` diu VALIDA |
| `dades-2` | Dades | **Resum de la Junta.** Pic de classes al matí i a la tarda, aules que falten o sobren per mida, sessions mogudes per titulació en percentatge i excepcions. Primer sobre la partida, i al final sobre el 5.2. | `nivell2/junta.py`, `resultats/nivell2/junta/` | `python -m nivell2.junta <proposta>` escriu la pàgina amb els quatre camps |
| `frontend-2` | Frontend | Connectar la graella a les propostes reals i afegir-hi la pàgina de la Junta. | `app/pagines/part2.py`, `app/pagines/junta.py`, `app/components/graella.py`, `app/test_part2.py` | Tests verds, i l'app mostra el 5.1 i el 5.2 |

## Fase 3 · Sobre el 5.2 congelat

| Títol | Rol | Tasca | Fitxers permesos | Fet quan |
|---|---|---|---|---|
| `backend-3` | Backend | **5.3 Imprevistos**, canviant el mínim respecte del 5.2. | `nivell2/s53.py`, `resultats/nivell2/5.3/` | `check … --escenari paquet/escenaris/contingencies --referencia <5.2>` diu VALIDA, i es mostren els canvis respecte de la referència |
| `backend-4` | Backend | **5.4 Grau nou**: col·locar les 235 sessions i dir quina de les quatre respostes és, amb la prova si cal. | `nivell2/s54.py`, `nivell2/cabuda.py`, `resultats/nivell2/5.4/` | `check … --escenari paquet/escenaris/grau-nou-40` diu VALIDA, o hi ha la prova per recompte o per INFEASIBLE |

## Fase 4 · Només si sobra temps

| Títol | Rol | Tasca |
|---|---|---|
| `backend-5` | Backend | Alternatives per a la Junta: el desdoblament de PAUL i SEM i les fusions de classes amb el mateix docent. |

## Decidit

- Res que surti de les dades del repte va a git: `.gitignore` ignora `resultats/`, `dades/` i `*.csv`. Les propostes es queden al Mac i es lliuren al jurat directament.

## Part 3 · Assistent d'IA (`.plans/part3-ia-spec.md`)

Tres tasques en paral·lel, cada una al seu worktree. La base del zip ja és a `app/xat/`: `servidor.py` (el `xat_ia.py` original), `web/xat-ia.js`, `web/xat-ia.css`, `instruccions.md` (el prompt aprovat), `GUIA-ZIP.md` (com funciona el widget) i `env.exemple`.

**Contracte entre les tres peces** (perquè no s'esperin):

- `app/xat/eines.py` exposa `EINES: list[dict]` (definicions de tools en format OpenAI: `{"type": "function", "function": {"name", "description", "parameters"}}`) i `executa(nom: str, args: dict) -> dict`. `executa` no llença mai excepcions: torna `{"ok": True, "resultat": …, "id_sessio": [...], "consulta": "…"}` o `{"ok": False, "error": "…"}`.
- `app/xat/servidor.py` exposa `arrenca(port: int = 8502) -> str`. Arrenca un sol cop un `ThreadingHTTPServer` de la biblioteca estàndard en un fil dimoni, amb `GET` i `POST /api/xat` (el contracte del zip) i CORS per a `http://localhost:8501` i `http://127.0.0.1:8501`. Torna l'adreça de l'API. Si el port està ocupat per un servidor seu, el reaprofita.
- `app/xat/widget.py` exposa `posa_widget(pantalla: dict | None)`: arrenca el servidor (amb `st.cache_resource`), injecta el JS i el CSS a la pàgina un sol cop i crida `XatIA.pantalla(pantalla)` a cada renderitzat. `pantalla = {"resum", "text", "preguntes"}`.

| Títol | Rol | Tasca | Fitxers permesos | Fet quan |
|---|---|---|---|---|
| `p3-backend-1` | Backend | **Servidor i bucle d'eines.** Adapta `servidor.py`: llegeix el `.env` de l'arrel del repositori, envia `tools` a la IA, executa les crides amb `eines.executa`, posa cada resultat al missatge `tool` dins de `<dades>…</dades>`, i fa com a molt 6 voltes per pregunta. El text final surt en directe (SSE com al zip). Mantén la IA de reserva i `IA_PROVA=1`; en mode de prova ha de fer servir almenys una eina falsa. Afegeix `arrenca()`. | `app/xat/servidor.py`, `app/xat/test_servidor.py` | `pytest app/xat/test_servidor.py` passa amb una IA falsa i unes eines falses: validació de missatges, bucle de tools (una crida, diverses i el límit de 6), error d'eina, `<dades>`, CORS i flux SSE. Sense obrir cap port als tests. |
| `p3-dades-1` | Dades | **Eines.** `horari_grup`, `aules_lliures`, `ocupacio_aula`, `xifra`, `resultat_proposta`, `consulta_sql` (només un `SELECT`, com a molt 50 files i 5 s) i `prova_canvi` (amb `nivell2.reparacio.repara` i el verificador, sense desar res). `proposta` pot ser `avui`, `5.1`, `5.2`, `5.3` o `5.4`. Fes servir el que ja existeix (`nivell1.dades.connexio`, `servei.una`, `servei.validacio_part2`, les rutes de `nivell2.base`, que funcionen des d'un worktree). Cada resultat porta els `id_sessio` i la consulta feta. | `app/xat/eines.py`, `app/xat/test_eines.py` | `pytest app/xat/test_eines.py` passa amb un paquet inventat petit, i `python -m app.xat.eines` executa cada eina un cop sobre les dades reals i n'imprimeix només el nombre de files i els 3 primers `id_sessio`. |
| `p3-frontend-1` | Frontend | **Widget a l'app.** `widget.py` amb `posa_widget()`. A `app/app.py`: treu la pàgina «Pregunta-ho · aviat» (i la secció «Ajuda» si queda buida) i crida `posa_widget()` després de `pagina.run()`, amb una pantalla feta a partir de la pàgina oberta, el semestre, la setmana i el que hi hagi a `st.session_state` (proposta, grup o aula triats). Preguntes proposades per pàgina segons l'especificació. Colors del widget amb les variables `--xatia-*` iguals que `app/estil.css`. Streamlit és la 1.67. | `app/xat/widget.py`, `app/xat/web/xat-ia.css`, `app/xat/test_widget.py`, `app/app.py` | `pytest app/xat/test_widget.py` passa, i amb `IA_PROVA=1 streamlit run app/app.py` el botó surt a totes les pàgines, s'obre, «Veu: …» canvia en canviar de pàgina i una pregunta rep la resposta de prova. |

No toquis `app/pagines/part2.py`, `app/components/graella.py` ni `docs/RESUM-PRESENTACIO.md`: hi treballen altres sessions.

## Simplificació de les targetes i «Comprova-ho» (dg 8-11)

Especificació: `.plans/simplificacio-targetes-spec.md`. Dues tasques en paral·lel, cadascuna al seu worktree; no comparteixen cap fitxer. No toquis `app/app.py`, `app/servei.py`, `app/pagines/part2.py` ni `app/components/graella.py`.

| Títol | Rol | Tasca | Fitxers permesos | Fet quan |
|---|---|---|---|---|
| `s-targetes-1` | Frontend | **Targetes amb un propòsit clar.** Aplica el patró de targeta, les tres etiquetes d'estat i els textos de l'especificació a la portada, «Totes les respostes», el resum per a la Junta i els imprevistos. Les xifres «avui → amb la proposta» surten de les dades i dels informes del verificador (`servei.validacio_part2`, `nivell2.base.RESULTATS`), mai escrites a mà. | `app/textos.py`, `app/presentacio.py`, `app/components/vistes.py`, `app/components/taules.py`, `app/components/format.py`, `app/pagines/portada.py`, `app/pagines/preguntes.py`, `app/pagines/junta.py`, `app/pagines/imprevistos.py`, `app/estil.css`, `app/test_app.py`, `app/test_junta_app.py`, `app/test_imprevistos.py` | `.venv/bin/python -m pytest -q app` passa, i cap text visible fora dels plegables tècnics conté «5.2», «verificador oficial», «franja original», «heretat» ni «2027-W». |
| `s-xat-1` | Frontend | **«Comprova-ho» sota les respostes del xat.** Plegable tancat amb què s'ha consultat en paraules, els `id_sessio` amb botó «Copia» i la consulta, a partir de `consultes`, que el navegador ja rep i desa. | `app/xat/web/xat-ia.js`, `app/xat/web/xat-ia.css`, `app/xat/test_widget.py` | `.venv/bin/python -m pytest -q app/xat` passa, i amb `IA_PROVA=1` una resposta amb eina mostra el plegable tancat que en obrir-lo ensenya la consulta. |

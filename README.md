# UAB THE HACK! 2026 · Espais i horaris de l'Escola d'Enginyeria

Repositori de l'equip per al hackató (ds 7-11 8:00 → dg 8-11 15:00, Escola d'Enginyeria UAB). Repte: horaris i espais del curs 2027-28, per a Gestió Acadèmica.

- **Part 1:** diagnosi de l'ocupació d'aules (app Streamlit, `nivell1/` i `app/`).
- **Part 2:** proposta d'horari del 2n semestre que passa el verificador oficial (`nivell2/`).

## Com s'executa

Les dades del repte **no són en aquest repositori** i no s'hi poden afegir (`.gitignore` exclou `repte/`, `resultats/`, `dades/`, `*.csv`, `*.zip` i `*.xlsx`). Qui tingui accés al paquet oficial el posa a `repte/repte-horaris-escola/` (o indica'n la carpeta amb la variable `REPTE_DIR`).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export REPTE_DIR="$PWD/repte/repte-horaris-escola"
python -m nivell1.comprova        # ha d'acabar amb «25/25 comprovacions correctes»
streamlit run app/app.py          # http://localhost:8501, només des d'aquest ordinador
```

**Assistent (part 3).** El botó «Assistent» surt baix a la dreta de totes les pàgines. Per connectar-lo a la IA de l'event, posa al `.env` de l'arrel `IA_URL=https://api.quiver.ai/v1`, `IA_CLAU=<la clau>`, `IA_MODEL=arrow-2-telos` i, si vols reserva, `IA_RESERVA_MODEL=arrow-2` (vegeu `app/xat/env.exemple`). Sense clau, `IA_PROVA=1 streamlit run app/app.py` respon un text de prova. El servidor del xat arrenca sol dins de Streamlit, al port 8502.

L'esquema de les dades, amb files inventades, és a [docs/esquema-dades.md](docs/esquema-dades.md). Els passos per validar l'app són a [VALIDATION.md](VALIDATION.md).

## Què hi ha

| On | Què és |
| --- | --- |
| `nivell1/` | Consultes de la part 1 (DuckDB) i les comprovacions de les xifres |
| `nivell2/` | Proposta d'horari de la part 2 (CP-SAT) i lector del verificador |
| `app/` | App Streamlit per a Gestió Acadèmica |
| `.plans/` | Especificacions de cada part |
| `docs/DIARI.md` | Diari del projecte: idees, decisions, problemes, solucions i recaps, amb l'hora |
| `docs/` (altres) | Esquema de dades inventat, revisions, maquetes de disseny i idees per al pitch |
| `CLAUDE.md`, `AGENTS.md` | Com treballem i normes per als agents d'IA (Claude Code i Codex) |
| `.claude/skills/` | Skills del projecte: repartiment als subagents de Codex, recap, diari i guies de disseny |

## Ús d'IA

### Models

| Eina | Model i versió | Per a què |
| --- | --- | --- |
| Claude Code (app d'escriptori de Claude) | Claude Opus 5.5 (`claude-opus-5-5`) | Dues sessions d'orquestració, una per a la part 1 i una per a la part 2. Preguntar a l'equip, escriure especificacions, repartir tasques, revisar, unir branques, fer commits, provar l'app al navegador i escriure documents i el diari. |
| Codex (compte ChatGPT de l'equip) | `gpt-6.1-sol`, esforç *medium* (alguns reintents i revisions, *high*) | Subagents que programen per rols (dades, backend, frontend), cadascun a la seva branca. També una revisió com a jurat i mentor (només lectura). |
| quiver.ai, el LLM de l'event (API Responses, `https://api.quiver.ai/v1`) | `arrow-2-telos` (principal) i `arrow-2` (reserva) | L'assistent de la part 3: respon les preguntes de Gestió Acadèmica cridant eines nostres (horari d'un grup, aules lliures, xifres de la part 1, resultats 5.1–5.4, SQL de lectura i prova de canvis amb el verificador). Sota cada resposta, el servidor mostra les consultes fetes i els `id_sessio`. |

Les sessions de Codex s'executen sense xarxa dins de l'ordinador. Aquest límit és del sandbox local: el que Codex llegeix o executa sí que s'envia als servidors d'OpenAI perquè el model ho processi. El mateix passa amb Claude Code i els servidors d'Anthropic.

### Ús de les dades del repte, abans i després de la restricció

**Abans (ds 7-11, fins al vespre).** Segons l'equip, l'organització ens va comunicar al principi que podíem treballar amb les dades del repte fent servir IA. Amb aquesta autorització:

- Claude Code i els subagents de Codex van llegir fitxers del paquet de dades (per entendre'n l'esquema, revisar files i comprovar resultats).
- També van executar consultes i scripts sobre aquestes dades, i en van llegir les sortides.

Una part d'aquest contingut va passar, per tant, pels serveis d'Anthropic i d'OpenAI. No tenim un inventari complet de quines files o valors concrets s'hi van enviar. Aquesta autorització inicial és el que ens va comunicar l'equip; no l'hem verificada pel nostre compte.

**Després (ds 7-11 al vespre).** L'organització ens va comunicar una restricció: les dades no es poden fer servir amb IA. L'equip ho atribueix a un malentès entre l'organització i la Junta. Des de llavors:

- Els agents treballen amb l'esquema i les files inventades de `docs/esquema-dades.md`. Poden executar el codi del projecte, però només en mostren recomptes, errors sense valors reals i veredictes (`AGENTS.md`).
- `.claude/settings.json` prohibeix a Claude Code llegir `repte/`, `resultats/` i `dades/`. És una barrera de configuració, no una garantia: una ordre indirecta encara les podria llegir.
- `.gitignore` exclou les dades i els resultats derivats, i l'app només escolta a `localhost`.
- Hem tret els identificadors i exemples reals (sessions, docents, codis i noms d'assignatura, grups i aules) dels documents, les proves, les maquetes i l'app, i els hem canviat per exemples inventats.

Aquesta neteja és local i del repositori. No desfà el que ja s'havia enviat a Anthropic o a OpenAI abans de la restricció; el que aquests serveis en conservin depèn de les seves polítiques de retenció.

Guia de l'equip: https://claude.ai/artifact/VeteakMwu7Rejbfu4uDqzL

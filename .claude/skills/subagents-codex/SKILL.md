---
name: subagents-codex
description: Reparteix i llança la programació del hackató a subagents de Codex (models d'OpenAI del compte ChatGPT) amb tres rols fixos —frontend, backend i dades— i coordina les seves preguntes, resultats i integració des de la sessió principal de Claude. Fes-la servir quan l'especificació ja és a .plans/ i toca programar, quan l'equip digui «llança els subagents», «reparteix les tasques», «passa-ho a Codex», «quin subagent fa això», o per respondre o reprendre un subagent que ha tornat QUESTION o BLOCKED. No facis servir subagents de Claude Code (Agent) per programar.
---

# Subagents de Codex per rols

## Com treballem

- **Un sol ordinador.** L'equip (les persones) decideix junt, pas a pas, davant d'aquesta sessió de Claude.
- **Claude és l'orquestrador** i fa el rol d'**integració**: reparteix la feina, pregunta a l'equip, revisa, uneix, fa els commits, prova al navegador i publica a Cloudflare.
- **La programació la fan subagents de Codex** (ChatGPT) amb `codex_run`, un per rol. Mai subagents de Claude Code per programar.
- Tots els subagents **pregunten en lloc de suposar**. Les preguntes arriben a l'equip a través de Claude.

## Els rols

| Rol | Qui | Què fa | Carpetes habituals |
| --- | --- | --- | --- |
| Frontend | Subagent de Codex | Pantalles, components, estils, estats de càrrega/error/buit, dades simulades mentre no hi ha API | `app/`, `src/`, `components/`, `public/` |
| Backend | Subagent de Codex | API, lògica, emmagatzematge, connexió amb les APIs del repte, proves | `api/`, `server/`, `lib/`, `worker/` |
| Dades | Subagent de Codex | Netejar i analitzar dades, càlculs, models, optimització, fitxers de dades per a la demo | `data/`, `scripts/`, `notebooks/` |
| Integració | Claude (sessió principal) | Unir branques, commits, desplegament (`cf-write wrangler`, amb permís), provar al navegador, diari, recap | tot el repositori |

Les carpetes exactes les fixa `.plans/tasques.md`: cada tasca diu quins fitxers pot tocar. Dos subagents no toquen mai el mateix fitxer.

## Abans de llançar

1. Ha d'existir l'especificació a `.plans/` (si no, `/jmo-workflow:interview`).
2. Ha d'existir `.plans/tasques.md` amb, per a cada tasca: rol, objectiu, fitxers permesos i criteri de «fet» (una ordre que es pugui executar). Si no hi és, crea-la a partir de l'especificació i ensenya-la a l'equip abans de seguir.
3. Un worktree per rol, des de l'arrel del repositori:
   ```bash
   git worktree add ../hack-frontend -b frontend
   git worktree add ../hack-backend -b backend
   git worktree add ../hack-dades -b dades
   ```

## Llançar un subagent

`codex_run` amb:

- `cwd`: el worktree del rol (camí absolut)
- `model`: `gpt-6.1-sol` · `effort`: `medium` (si torna BLOCKED o proves vermelles: `high`)
- `write`: `true` · `network`: `none` (només `local` si ha d'arribar a un servidor local)
- `title`: `<rol>-<n>` (p. ex. `frontend-1`), únic

Llança les tasques independents de rols diferents **en paral·lel** (diverses crides `codex_run` al mateix missatge). Passen a segon pla i n'arriba l'avís quan acaben.

Prompt (autosuficient: Codex no ha vist la conversa):

```text
Ets el subagent de [FRONTEND | BACKEND | DADES] d'un equip de 3–4 persones a un hackató de 31 hores (UAB THE HACK! 2026).
Persona per a qui fem el producte: [persona i problema en una frase].
Llegeix .plans/[nom]-spec.md i .plans/tasques.md. Fes només la tasca [n]: [títol].
Només pots crear o modificar: [fitxers o carpetes]. No toquis res més.
Està feta quan: [ordre que ho demostra i resultat esperat].

REGLA DE PREGUNTES. Abans de programar, llista el que l'especificació no deixa prou clar (dades, formats, textos, disseny, què passa si hi ha errors). Si un punt canvia el resultat i no el pots deduir del repositori, NO suposis: acaba amb STATUS QUESTION i escriu preguntes numerades i concretes, cadascuna amb 2–3 opcions i la que recomanes. Si són detalls menors, tria l'opció més simple i apunta-la a «SUPÒSITS».

En acabar, respon amb: (1) què has canviat, en 3 línies; (2) com ho has comprovat (ordre i sortida); (3) SUPÒSITS; (4) problemes que has trobat.
```

## Quan un subagent torna QUESTION

1. Ajunta les preguntes de tots els subagents que esperen.
2. Fes-les a l'equip amb `AskUserQuestion` (màxim 4 per tanda), amb les opcions del subagent i la recomanada primer. Digues de quin subagent ve cada pregunta.
3. Respon a cada subagent amb `codex_send({thread: "<title>", message: "<respostes>"})`.
4. Apunta cada resposta al diari com a DECISIÓ (skill `diari`).

Revisa també els SUPÒSITS de cada resultat: si n'hi ha un que canvia el que veurà la persona o el jurat, confirma'l amb l'equip.

## Quan un subagent torna DONE

1. Mira `FILES CHANGED` i treu-ne la brossa (`__pycache__`, fitxers temporals).
2. Executa tu l'ordre de «fet». Si falla, torna-li amb `codex_send` i la sortida de l'error.
3. Fes el commit a la branca del rol (Codex no pot fer commits) i, si funciona, uneix-la a `main`.
4. Apunta al diari què ha fet (IA) i qualsevol problema.

## Quan torna BLOCKED

Torna-ho a provar amb `effort: high` i més context (l'error, el fitxer, què s'esperava). Si torna a fallar, porta el problema a l'equip amb opcions: simplificar la tasca, fer-la amb dades simulades o deixar-la.

## Coses que Codex no pot fer

Fer commits, obrir ports per a proves, navegar per la web, publicar. Tot això ho fa Claude com a integració.

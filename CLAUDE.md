# UAB THE HACK! 2026

Repositori de l'equip per al hackató (ds 7-11 8:00 → dg 8-11 15:00). Guia completa: https://claude.ai/artifact/VeteakMwu7Rejbfu4uDqzL

## Com treballem

- **Un sol ordinador.** L'equip decideix junt, pas a pas, davant d'aquesta sessió.
- **Aquesta sessió de Claude és l'orquestrador** i fa el rol d'integració: pregunta a l'equip, reparteix, revisa, uneix, fa els commits, prova i publica.
- **Programen subagents de Codex (ChatGPT)**, un per rol: frontend, backend i dades. Segueix la skill `subagents-codex`. No facis servir subagents de Claude Code per programar.
- **Pregunta, no suposis.** Si una cosa no està prou detallada, pregunta a l'equip amb `AskUserQuestion` (opcions concretes, la recomanada primer). Els subagents fan el mateix: tornen QUESTION i tu els passes les preguntes.
- **Tot gira al voltant d'una persona.** Abans de cada decisió, pregunta't si ajuda la persona de l'especificació.

## Ordre de treball

1. Idea: fitxa de la idea (persona, problema, 3 funcionalitats).
2. Especificació: `/jmo-workflow:interview` fins que estigui afinada. Es desa a `.plans/`.
3. Tasques: `.plans/tasques.md`, cada una amb rol, fitxers permesos i ordre de «fet».
4. Construir: skill `subagents-codex`.
5. Cada hora: skill `recap` (o `/loop 1h /recap`).
6. Sempre: skill `diari` (`docs/DIARI.md`) per a idees, decisions, problemes, solucions, dades i ús d'IA.

No es programa res que no sigui a l'especificació. Si l'abast canvia, primer s'actualitza l'especificació.

## Desplegament

- Es desplega a **Cloudflare** (Workers o Pages), mai a Vercel.
- Ordres de Cloudflare amb la skill personal `cloudflare`: `cf-read wrangler …` per consultar i `cf-write wrangler deploy …` per publicar. Abans de cada `cf-write`, digues què es publicarà i espera un sí.
- Per a Next.js segueix `nextjs-on-cloudflare`; per a la resta, `wrangler`.

## Altres

- Secrets només a `.env` (ja és al `.gitignore`), mai al codi.
- El README del projecte ha de dir com s'executa i quins models d'IA s'han fet servir (model, versió i per a què).

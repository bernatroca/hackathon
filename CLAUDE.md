# UAB THE HACK! 2026

Repositori de l'equip per al hackató (ds 7-11 8:00 → dg 8-11 15:00). Guia completa: https://claude.ai/artifact/VeteakMwu7Rejbfu4uDqzL

## Desplegament

- Es desplega a **Cloudflare** (Workers o Pages), mai a Vercel.
- Les ordres de Cloudflare passen per la skill personal `cloudflare`: `cf-read wrangler …` per consultar i `cf-write wrangler deploy …` per desplegar. Abans de cada `cf-write`, digues què es publicarà i espera un sí.
- Per a Next.js segueix la skill `nextjs-on-cloudflare`; per a la resta, `wrangler`.

## Treball

- L'especificació és a `.plans/`. No es programa res que no hi sigui; si l'abast canvia, primer s'actualitza l'especificació.
- Apunta idees, decisions, problemes, solucions i ús d'IA amb la skill `bitacola` (`docs/BITACOLA.md`).
- Backend o lògica amb proves → Codex (`codex_run`, `gpt-6.1-sol`, effort medium). Revisions → `codex_ask`.
- Secrets només a `.env` (ja és al `.gitignore`), mai al codi.
- El README ha de dir com s'executa i quins models d'IA s'han fet servir (model, versió i per a què).

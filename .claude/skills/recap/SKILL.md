---
name: recap
description: Fa la parada d'una hora del hackató, de 5 minuts. Resumeix què han fet els subagents de Codex i l'equip des de l'últim recap, què està bloquejat, quines preguntes queden pendents i si la demo funcionaria ara, i proposa les 3 properes tasques. Fes-la servir cada hora (amb `/loop 1h /recap`), o quan l'equip digui «recap», «parada», «on som» o «resum de l'hora».
---

# Recap de cada hora

L'objectiu és que tot l'equip sàpiga on som en 5 minuts i decideixi junt el pas següent. Sigues curt.

## Passos

1. Llegeix l'estat:
   - `codex_status`: subagents en marxa, acabats, i els que esperen una resposta (QUESTION) o estan bloquejats (BLOCKED).
   - `git log --oneline --since="70 minutes ago" --all`.
   - El diari (`docs/DIARI.md`) des de l'últim RECAP.
2. Comprova la demo: executa l'ordre de «fet» de la funcionalitat principal (de `.plans/tasques.md`), o obre la URL desplegada si n'hi ha.
3. Escriu el recap així (12 línies com a màxim):

```text
RECAP [ds 15:00]
Fet aquesta hora: …
En marxa: frontend-… · backend-… · dades-…
Bloquejat / preguntes pendents: …
Demo ara: SÍ / NO (què falta)
Temps fins a la congelació (dg 2:00): … h
Proposta per a la propera hora:
1. …  2. …  3. …
```

4. Pregunta a l'equip amb `AskUserQuestion` si segueixen la proposta (opcions: «Seguim així», «Canviem prioritats», «Simplifiquem»). Si hi ha preguntes pendents dels subagents, fes-les en aquesta mateixa tanda.
5. Apunta el recap al diari com a RECAP (skill `diari`).

## Quan anem tard

Si falten menys de 6 hores per a la congelació i la demo encara no funciona de principi a fi, proposa retallar: dades simulades, treure la funcionalitat menys important, o fer només el recorregut de la demo.

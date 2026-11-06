---
name: diari
description: Apunta al Diari del projecte (docs/DIARI.md) les idees (també les descartades), decisions, problemes, solucions, dades del problema, recaps i l'ús d'IA del hackató, amb l'hora. Fes-la servir quan l'equip digui «apunta», «al diari», «hem tingut un problema», «hem decidit», quan un subagent prengui un supòsit o l'equip respongui una pregunta d'un subagent, quan es resolgui un error que ha costat més de 15 minuts, quan es canviï l'abast o la idea, i quan es demani el resum per a la presentació.
---

# Diari del projecte

El diari és la memòria de l'equip i la matèria primera de la presentació: quin problema hem triat i per què, què hem descartat, què ha fallat i com ho hem resolt, i com hem fet servir la IA (el jurat ho pot demanar i en edicions anteriors era obligatori documentar-ho).

## On

`docs/DIARI.md` a l'arrel del repositori. Si no existeix, crea'l amb aquesta capçalera:

```markdown
# Diari del projecte — UAB THE HACK! 2026

Equip: … · Repte: … · Persona: …
```

## Com apuntar

Afegeix sempre al final; no reescriguis entrades anteriors. Una entrada per fet:

```markdown
### [ds 14:20] PROBLEMA · L'API del repte torna 429
- Què ha passat: …
- Com ho hem resolt: … (o «obert»)
- Temps perdut: ~30 min
- Per a la presentació: …
```

| Tipus | Quan |
| --- | --- |
| IDEA | Una idea triada o descartada, amb el motiu |
| DECISIÓ | Una tria d'abast, stack, disseny o dades, o la resposta de l'equip a una pregunta d'un subagent |
| PROBLEMA | Un error, bloqueig o canvi de pla |
| SOLUCIÓ | Com s'ha resolt un problema anterior (enllaça'l pel títol) |
| IA | Quin subagent o model ha fet què (Codex `gpt-6.1-sol` i effort, Claude, skills) i on ha fallat |
| DADA | Una xifra o notícia del problema amb l'enllaç a la font, per a la presentació |
| RECAP | El resum de la parada de cada hora (skill `recap`) |
| DEMO | Canvis al guió de la demo |

L'hora és la real (`date +"%a %H:%M"`), en format `ds 14:20` o `dg 03:10`. Sigues breu: 2–5 línies, frases curtes, en català. Si falta informació, apunta el que tinguis i pregunta només el que falti.

## Resum per a la presentació

Quan es demani, llegeix tot el diari i escriu `docs/RESUM-PRESENTACIO.md` amb:

1. El problema i la persona, amb les DADES (xifra + font).
2. Les 2–3 idees descartades i per què vam triar aquesta.
3. Els 3 problemes més difícils i com els vam resoldre.
4. Com hem fet servir la IA: Claude com a orquestrador, subagents de Codex per rol, models i versions, i què vam decidir nosaltres.
5. Què queda per fer, per respondre «què no heu acabat?» amb honestedat.

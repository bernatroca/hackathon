---
name: bitacola
description: Apunta a docs/BITACOLA.md les idees (també les descartades), decisions, problemes, solucions i l'ús d'IA del hackató, amb hora. Fes-la servir quan l'equip digui «apunta», «a la bitàcola», «hem tingut un problema», «hem decidit», quan es resolgui un error que ha costat més de 15 minuts, quan es canviï l'abast o la idea, i quan es demani el resum per a la presentació.
---

# Bitàcola del hackató

La bitàcola és la memòria de l'equip i la matèria primera del pitch: quin problema hem triat i per què, què hem descartat, què ha fallat i com ho hem resolt, i com hem fet servir la IA (el jurat ho pot demanar i en edicions anteriors era obligatori documentar-ho).

## On

`docs/BITACOLA.md` a l'arrel del repositori. Si no existeix, crea'l amb aquesta capçalera:

```markdown
# Bitàcola — UAB THE HACK! 2026

Equip: … · Repte: … · Persona: …
```

## Com apuntar

Afegeix sempre al final (no reescriguis entrades anteriors). Una entrada per fet, amb aquest format:

```markdown
### [ds 14:20] PROBLEMA · L'API del repte torna 429
- Què ha passat: …
- Com ho hem resolt: … (o «obert»)
- Temps perdut: ~30 min
- Lliçó per al pitch: …
```

Tipus d'entrada (la paraula en majúscules després de l'hora):

| Tipus | Quan |
| --- | --- |
| IDEA | Una idea que es planteja, triada o descartada (digues per què) |
| DECISIÓ | Una tria d'abast, stack, disseny o dades, amb el motiu |
| PROBLEMA | Un error, bloqueig o canvi de pla |
| SOLUCIÓ | Com s'ha resolt un problema anterior (enllaça'l pel títol) |
| IA | Quin model o agent ha fet què (Claude, Codex amb model i effort, skills), i on ha fallat |
| DADA | Una xifra o notícia del problema amb l'enllaç a la font, per a la diapositiva d'evidència |
| DEMO | Canvis al guió de la demo |

L'hora és la real (`date +"%a %H:%M"`), en format `ds 14:20` o `dg 03:10`. Sigues breu: 2–5 línies per entrada, frases curtes, en català.

Si la persona dona poca informació, apunta el que tinguis i pregunta només el que falti per a «Com ho hem resolt».

## Resum per a la presentació

Quan es demani el resum, llegeix tota la bitàcola i escriu `docs/RESUM-PITCH.md` amb:

1. El problema i la persona, amb les DADES (xifra + font).
2. Les 2–3 idees descartades i per què vam triar aquesta.
3. Els 3 problemes més difícils i com els vam resoldre (per a la diapositiva de reptes tècnics).
4. Com hem fet servir la IA: models, versions, per a què, i què vam fer a mà.
5. Què queda per fer (per respondre «què no heu acabat?» amb honestedat).

# Diari del projecte — UAB THE HACK! 2026

Equip: … · Repte: horaris i espais Escola d'Enginyeria 2027-28 · Persona: …

### [ds 12:36] DECISIÓ · Repte: horaris i espais de l'Escola d'Enginyeria 2027-28
- Repte de l'Escola d'Enginyeria. Material a SharePoint (enunciat per nivells, CSV del pla docent, verificador en Python, plànols, diapositives).
- Prova inicial: `python -m horaris check paquet/proposta_partida.csv --semestre 2` ha de donar NO VALIDA (és l'horari d'avui).
- Dades pseudonimitzades: es queden al Mac (`repte/`, ignorat per git). No es pugen a GitHub.
- L'equip decideix que els agents (Claude i Codex) poden llegir les dades.
- Per al nivell 3, cal fer servir el LLM de l'event.

### [ds 12:44] PROBLEMA · Podem passar les dades del repte a Codex?
- L'enunciat diu que les dades «no les envieu a serveis externs». Codex corre als servidors d'OpenAI, que és un servei extern.
- Això canvia la decisió de les 12:36: de moment, ni Claude ni Codex llegeixen files reals de les dades, només codi, capçaleres i recomptes.
- Preguntem a l'organització si podem fer servir Codex sobre les dades. Pla B: una còpia sintètica (mateix format, valors inventats) per programar, i el codi s'executa amb les dades reals al Mac.

### [ds 12:46] DECISIÓ · L'organització permet fer servir Codex amb les dades
- L'equip ho ha preguntat a l'organització i la resposta és que sí.
- Claude i els subagents de Codex poden llegir les dades del repte. No fem la còpia sintètica.
- Es manté la resta: les dades no es publiquen ni es pugen a GitHub, no s'intenta identificar ningú, i el nivell 3 fa servir el LLM de l'event.

### [ds 13:07] DECISIÓ · Especificació de la part 1 (anàlisi)
- Fem les parts per ordre: 1 (anàlisi), 2 (solver), 3 (assistent). Cada part acaba amb una mini demo d'un minut; la demo final és de 3 minuts i es fa amb l'eina de vídeo de Claude en una conversa a part.
- Part 1: app Streamlit local (no es publica), DuckDB amb SQL visible, portada amb 5 troballes, cada una amb xifra, frase, gràfic i com s'ha calculat.
- «Hi cap el matí?»: pic per blocs de 30 min, ocupació, i hores-aula per mida d'aula (si una mida no hi cap, és impossible).
- Setmana típica (mediana) per al mapa i pitjor setmana per a «hi cap». Tots dos semestres, amb selector.
- Preguntes afegides: seients buits, hores mortes, canvis d'aula, dobles amb grup de matí, docents a cavall, marge per al grau nou. «Pla contra realitat» fora: el fitxer del GERES no és al paquet.
- Feta quan `python -m nivell1.comprova` quadra amb les xifres de l'enunciat i l'app ho mostra.
- Rols: dades fa nivell1/ (SQL i xifres), frontend fa app/. Backend comença a mirar el verificador per a la part 2.
- Espec: .plans/nivell1-analisi-spec.md

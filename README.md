# UAB THE HACK! 2026 · Espais i horaris de l'Escola d'Enginyeria

Repositori de l'equip per al hackató (ds 7-11 8:00 → dg 8-11 15:00, Escola d'Enginyeria UAB). Repte: horaris i espais del curs 2027-28, per a Gestió Acadèmica.

- **Part 1:** diagnosi de l'ocupació d'aules (app Streamlit, `nivell1/` i `app/`).
- **Part 2:** proposta d'horari del 2n semestre que passa el verificador oficial (`nivell2/`).
- **Part 3:** assistent per a Gestió Acadèmica (`app/xat/`).

## Com s'executa

Per provar la web i l'Assistent en un altre ordinador calen tres coses: aquest repositori, el paquet oficial del repte i `lliurament-nivell2.zip` (les propostes de la part 2; es lliura amb l'entrega, no és a GitHub). Cal **Python 3.11 o més nou** (entorn provat: Python 3.13).

1. Poseu el paquet oficial a `repte/repte-horaris-escola/` (o indiqueu-ne la carpeta amb la variable `REPTE_DIR`).
2. Descomprimiu el ZIP a l'arrel del repositori: crea `resultats/nivell2/`, que fan servir «Horari proposat», «Imprevistos», «Resum per a la Junta» i l'Assistent.
3. Per a l'Assistent: `cp app/xat/env.exemple .env` i poseu la clau de la IA de l'event (quiver.ai) a `IA_CLAU=`. La URL i el model ja hi són.
4. Instal·leu i arrenqueu:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export REPTE_DIR="$PWD/repte/repte-horaris-escola"
streamlit run app/app.py          # obre http://localhost:8501
```

Per comprovar-ho tot:

```bash
python -m nivell1.comprova        # ha d'acabar amb «33/33 comprovacions correctes»
python -m pytest app nivell1 nivell2 -q -p no:cacheprovider  # cal REPTE_DIR i resultats/; uns 2 minuts
```

Resultat de referència de les proves: 873 correctes i 1 omesa.

**Assistent (part 3).** El botó «Assistent» surt baix a la dreta de totes les pàgines. Sense clau, `IA_PROVA=1 streamlit run app/app.py` respon un text de prova. El servidor del xat arrenca sol dins de Streamlit, en un port local lliure que tria el sistema (només accepta peticions de localhost). També es pot preguntar des de la terminal: `python -m app.xat.pregunta "Quantes aules queden lliures dimarts a les 10?" --proposta 5.2` (vegeu [lliurament/com-es-comprova-l-assistent.md](lliurament/com-es-comprova-l-assistent.md)).

L'esquema de les dades, amb files inventades, és a [docs/esquema-dades.md](docs/esquema-dades.md). Els passos per validar l'app són a [VALIDATION.md](VALIDATION.md).

## Part 2 · Lliurament i reproducció

Descomprimiu `lliurament-nivell2.zip` a l’arrel del repositori: crea `resultats/nivell2/5.1/`–`5.4/`,
els resums de la Junta a `resultats/nivell2/junta/<proposta>/` i les graelles a `graelles/`.
`LLEGEIX-ME.md`, dins el ZIP, recull els veredictes. Cada pregunta inclou el README amb l’ordre exacta
de reproducció o republicació, temps, llavor, pistes necessàries i ordre oficial del jurat. Les pistes i comparacions
citades també s’inclouen al ZIP. Generar una proposta executa el solver; regenerar els documents
derivats conserva les propostes i relaxacions existents:

```bash
python -m nivell2.xifres_lliurament 5.1 5.2 5.3 5.4
python -m nivell2.junta resultats/nivell2/5.2/proposta.csv --sortida resultats/nivell2/junta/5.2
python -m nivell2.verificacio 5.2  # substituïu 5.2 per 5.1, 5.3 o 5.4
python -m nivell2.empaqueta --sortida lliurament
```

`verificacio` desa l’informe i les violacions oficials. `empaqueta` revalida en fitxers temporals,
comprova les persones, regenera els derivats i crea el ZIP només si tots els contractes són correctes.
Per executar directament el verificador oficial (exemple 5.2), amb `REPTE_DIR` exportat:

```bash
REPOSITORI="$PWD"
cd "$REPTE_DIR"
python -m horaris check "$REPOSITORI/resultats/nivell2/5.2/proposta.csv" --semestre 2 --relaxacions "$REPOSITORI/resultats/nivell2/5.2/relaxacions.csv" --json "$REPOSITORI/resultats/nivell2/5.2/informe.json" --violacions "$REPOSITORI/resultats/nivell2/5.2/violacions.csv"
cd "$REPOSITORI"
```

El 5.1 necessita `--nomes-aules`; el 5.3 i el 5.4 necessiten l’escenari i la referència 5.2:
seguiu l’ordre completa del README de cada pregunta. El repte oficial i `dades/alumnes_sense_dada.json`
es lliuren separadament i no es versionen. Aquest JSON aporta les estimacions d’alumnat per regenerar
el resum de la Junta. Sense el fitxer, consulteu el `junta.json` ja generat que inclou el ZIP;
el resum HTML es pot obrir directament sense recalcular el model.

## Preguntes des de la terminal

Des de l'arrel del repositori, amb `REPTE_DIR` exportat. Totes s'han provat a `main`.

**Part 2 · el verificador oficial.** Torna el veredicte de cada proposta:

```bash
python -m nivell2.verificacio 5.1   # 5.1 | VALIDA
python -m nivell2.verificacio 5.2   # 5.2 | VALIDA AMB RELAXACIONS DECLARADES
python -m nivell2.verificacio 5.3   # 5.3 | VALIDA AMB RELAXACIONS DECLARADES
python -m nivell2.verificacio 5.4   # 5.4 | VALIDA AMB RELAXACIONS DECLARADES
```

L'ordre del jurat, amb l'horari d'avui (surt NO VALIDA) i amb la nostra 5.2:

```bash
cd "$REPTE_DIR"
python -m horaris check paquet/proposta_partida.csv --semestre 2
python -m horaris check "$OLDPWD/resultats/nivell2/5.2/proposta.csv" --semestre 2 --relaxacions "$OLDPWD/resultats/nivell2/5.2/relaxacions.csv"
cd "$OLDPWD"
```

**Part 3 · preguntes a l'assistent.** Cal la clau de la IA al `.env`. Imprimeix la resposta i, a sota, les consultes que ha fet, per comprovar-les:

```bash
python -m app.xat.pregunta "Quantes aules queden lliures dimarts a les 10?" --proposta 5.2 --setmana típica
python -m app.xat.pregunta "Quantes classes canvien d'aula amb els imprevistos del 5.3?" --proposta 5.3
python -m app.xat.pregunta "El grau nou de 40 places hi cap? Quantes classes del 5.2 es mouen?" --proposta 5.4
```

Respostes de referència: 6 aules ordinàries lliures, respectant les dues de reserva; 65 classes canvien d'aula al CSV i el verificador en compta 64, perquè no hi compta la classe cancel·lada; el grau nou hi cap i no es mou cap classe del 5.2. Per executar una eina sense la IA: `python -m app.xat.pregunta --sense-ia --eina aules_lliures --args '{"dia":"dimarts","hora_ini":"10","durada_min":60,"places_min":0,"proposta":"5.2","setmana":"típica"}'`.

## Què hi ha

| On | Què és |
| --- | --- |
| `nivell1/` | Consultes de la part 1 (DuckDB) i les comprovacions de les xifres |
| `nivell2/` | Proposta d'horari de la part 2 (CP-SAT) i lector del verificador |
| `app/` | App Streamlit per a Gestió Acadèmica |
| `app/xat/` | Assistent de la part 3 i eines de consulta del servidor |
| `.plans/` | Especificacions de cada part |
| `docs/DIARI.md` | Diari del projecte: idees, decisions, problemes, solucions i recaps, amb l'hora |
| `docs/` (altres) | Esquema de dades inventat, revisions, maquetes de disseny i idees per al pitch |
| `CLAUDE.md`, `AGENTS.md` | Com treballem i normes per als agents d'IA (Claude Code i Codex) |
| `.claude/skills/` | Skills del projecte: repartiment als subagents de Codex, recap, diari i guies de disseny |

## Ús d'IA

### Models

| Eina | Model i versió | Per a què |
| --- | --- | --- |
| Claude Code (app d'escriptori de Claude) | Claude Opus 5.5 (`claude-opus-5-5`) | Tres sessions d'orquestració (parts 1, 2 i 3) i subagents revisors en mode només lectura. Preguntar a l'equip, escriure especificacions, repartir tasques, revisar, unir branques, fer commits, provar l'app al navegador i escriure documents i el diari. |
| Codex (compte ChatGPT de l'equip) | `gpt-6.1-sol`, esforç *medium* (alguns reintents i revisions, *high*) | Subagents que programen per rols (dades, backend, frontend), cadascun a la seva branca. També una revisió com a jurat i mentor (només lectura). |
| quiver.ai, el LLM de l'event (API Responses, `https://api.quiver.ai/v1`) | `arrow-2-telos` (principal) i `arrow-2` (reserva) | L'assistent de la part 3: respon les preguntes de Gestió Acadèmica cridant eines nostres (horari d'un grup, aules lliures, xifres de la part 1, resultats 5.1–5.4, SQL de lectura i prova de canvis amb el verificador). Les xifres surten de les eines, i el servidor comprova cada xifra, aula i sessió de la resposta abans d'enviar-la. Sota cada resposta, «Comprova-ho» mostra les consultes fetes. |


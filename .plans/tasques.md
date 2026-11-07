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

# Especificació de la part 2 · Proposta d'horari

> **Estat.** Afinada amb l'equip (entrevista del ds 7-11). No es programa ni es publica res fins que l'equip doni l'OK.
> La graella setmanal espera que el disseny del nivell 1 estigui confirmat (`docs/disseny/`, opcions A, B i C) i en fa servir el mateix estil.

## La pregunta i la persona

La part 2 és el cor del repte i val el 50 % de la nota. Treballem el 2n semestre. La pregunta és: com faríem possible l'horari amb les línies mestres noves, i què costa?

Pensem en l'estudiant. Un bon horari és **rutinari**: cada setmana el mateix dia, la mateixa hora i la mateixa aula. També s'hi assembla al d'avui tant com es pugui, i qui va de tardes continua anant de tardes, tret que la regla 1 obligui a canviar-ho.

## Què lliurem

Cada pregunta es lliura amb:

- la proposta: un CSV `id_sessio,dia,h_ini,aula`, una fila per sessió;
- la sortida del verificador: `--json informe.json --violacions violacions.csv` (i `--relaxacions relaxacions.csv` si n'hi ha);
- la taula de xifres abans i després (vegeu «Com sabem que està fet»);
- una mini demo d'un minut.

Les preguntes són aquestes:

1. **5.1 Aules (5 %).** Amb l'horari d'avui, sense moure cap dia ni cap hora, donem aula a les 4.541 sessions que no en tenen. Es comprova amb `--nomes-aules`. Es premia que sigui bona: aula base per grup, pocs canvis d'aula entre classes seguides i pocs canvis respecte de l'aula d'avui.
2. **5.2 Torns nous (25 %).** Cada sessió va al torn que li toca segons la regla 1, i diem què costa. Hi afegim el resum de la Junta.
3. **5.3 Imprevist (10 %).** Partim del 5.2 i resolem quatre imprevistos alhora, canviant el mínim.
4. **5.4 Grau nou de 40 places (10 %).** Col·loquem les 235 sessions del 2n semestre sobre el 5.2.

I, un sol cop, la graella setmanal per aula de la proposta més avançada.

## Regles que ens posem (a més del verificador)

Les regles són per ordre de prioritat. Quan dues xoquen, guanya la primera.

1. **Les regles del verificador.** Cap relaxació en silenci: totes es declaren amb el motiu.
2. **La rutina és una regla dura.** Planifiquem per activitat (`activitat_id`), no per sessió. Totes les sessions d'una activitat van al mateix dia, la mateixa hora i la mateixa aula totes les setmanes. Només el 5.3 pot fer diferent una setmana concreta (sala reservada, avaria, recuperació).
3. **El torn de l'estudiant.** Al 5.1, al 5.3 i al 5.4 cap sessió no canvia de torn. Al 5.2 una sessió només canvia de torn si la regla 1 l'hi obliga. Mai no es mou cap a l'altre torn una sessió que ja és al seu.
4. **Mínims canvis respecte d'avui.** Un canvi d'hora o de dia pesa més que un canvi d'aula. Quan una sessió s'ha de moure, primer es prova el mateix dia; només si no hi cap, o si hi guanya molt, va a un altre dia.
5. **Aula base i passadís.** La teoria i els problemes d'un grup, a la mateixa aula o al mateix passadís (mateixa espina i planta).
6. **Poques hores mortes.** Les classes mogudes s'enganxen a les altres del grup aquell dia.

## 5.2: què es pot moure

- Es pot moure el dia, l'hora i l'aula de **qualsevol sessió movible**, no només de les que són fora de torn. Cada canvi té un cost, i el solver només mou una sessió que ja era bé si hi guanya prou (fer-hi cabre les altres, l'aula base, menys hores mortes).
- No es toquen les de GEI i GEET+GEST de 1r i 2n ni els PLAB. Una sessió no canvia ni de setmana ni de durada.
- Avui hi ha 2.008 sessions al torn equivocat (R1-TORN). Unes 246 movibles de 1r i 2n són a la tarda i passen al matí. El gruix, unes 1.770 de 3r, 4t, dobles i màsters, és al matí i passa a la tarda.
- **Excepcions a la regla 1, només si és impossible.** Ho demostrem amb un recompte (demanda contra oferta per franja i mida d'aula) o amb un INFEASIBLE del solver que no relaxi res. Si només és «no l'hem trobat», ho diem així. Una sessió amb excepció es queda al torn d'avui.
- El 5.2 no deixa lloc per al grau nou: és el 5.4 qui s'hi adapta.
- No calculem alternatives de torn: només la regla 1 tal qual.

## Alternativa per a la Junta: desdoblament per rotació (PAUL i SEM)

> **Decisió (ds 16:20).** El desdoblament **no va a les propostes lliurades** (5.1-5.4). Obligaria a declarar R3-AFORAMENT a unes 1.197 sessions (153 activitats), i qualsevol proposta VALIDA sense relaxacions passaria per davant. El verificador del jurat tampoc no veu la meitat B. A més, no cal: al nivell 1 cap mida d'aula falla al matí. Es fa com a alternativa per a la Junta, i només quan els quatre lliuraments estiguin fets i validats.

**Com seria:** tot grup de problemes (PAUL) o de seminari (SEM) movible de **més de 34 alumnes** es parteix en dues meitats. L'aula petita és un seminari o Q9/5014, totes de fins a 34 places. Un grup que hi cap sencer (34 alumnes o menys) no es parteix. **Sempre en dues meitats, mai en més parts:** un grup de 100 es parteix en dues meitats de 50, no en quatre de 25. Cada meitat va a l'aula més petita on hi càpiga (una meitat de 50 va a una aula de 48-50 o de 63). La teoria (TE) no es parteix.

**Amb parella (preferit): rotació.** Fan parella dues sessions X i Y del mateix grup d'alumnes (mateixa cohort i subgrup), movibles i de la mateixa durada.

- **1a hora:** la meitat A fa X en una aula petita, i la meitat B fa Y en una altra.
- **2a hora:** es canvien. Cadascú fa l'hora sencera de cada assignatura i ningú no té hores mortes.
- Les dues franges són seguides. Cada docent fa dues hores seguides a la seva aula.

**Sense parella:** es parteix igualment. Les dues meitats fan la mateixa assignatura, en dues hores seguides si es pot. Si no hi ha una hora seguida lliure, la segona meitat la fa un altre dia de la mateixa setmana, al mateix torn. L'hora lliure de cada meitat s'intenta posar a l'inici o al final del dia.

**Com ho escrivim per al verificador:**

- El CSV només té una fila per sessió: la de la meitat A (per a la rotació, X a la 1a hora i Y a la 2a).
- Es declara R3-AFORAMENT sobre aquestes sessions, amb el motiu «desdoblat en dues meitats» i on es fa l'altra meitat. És la via que dóna l'enunciat al 5.3 per desdoblar, perquè el format no permet afegir sessions.
- El verificador no veu la meitat B: ni l'aula, ni el docent, ni l'alumnat. Per això **el nostre model la reserva i en comprova els solapaments** (aula, docent, alumnat, reserva R8 i torn). La graella l'ensenya.

**Aules (TE, PAUL i SEM poden anar a aules docents i a seminaris):**

| Places | Aules | Grups TE | Grups PAUL | Grups SEM |
|---|---|---:|---:|---:|
| 1–34 | 9: 8 seminaris (10–34) i Q9/5014 (24) | 23 | 82 | 0 |
| 35–50 | 4: Q9/5013, Q9/5015, Q9/5022 (48) i Q9/5023 (50) | 16 | 101 | 6 |
| 51–63 | 2: Q9/5008 i Q9/5009 | 20 | 25 | 4 |
| 64–90 | 7: Q9/5024, Q9/5025 (88) i cinc de 90 | 51 | 4 | 0 |
| 91–160 | 7: dues de 100, dues de 117, dues de 130 i Q9/5006 (160) | 14 | 1 | 0 |

(Hi ha 14 grups sense dada d'alumnes. Comptem els grups del 2n semestre un cop cadascun, sense PLAB ni dobles.)

**Per què ho fem:** hi ha 101 grups de problemes de 35 a 50 alumnes, i només 4 aules d'aquesta mida. Avui ocupen aules de 63 o de 90 places, que són les que necessita la teoria. Partits en meitats, caben en un seminari i alliberen les aules mitjanes. Cada desdoblament compta com a canvi a la taula de xifres, i la Junta veu quants n'hem fet i quantes hores d'aula mitjana alliberen.

> Per comprovar en programar: 8 seminaris i Q9/5014 potser no basten per a totes les meitats a l'hora punta. Si no hi caben, la meitat va a la següent aula més petita lliure, i ho comptem.

## Fusió de classes amb el mateix docent (proposta per a la Junta)

No té sentit que un docent faci dues vegades la mateixa classe a grups que hi caben junts. El 5.2 es lliura **sense fusions** (vàlid net). Al resum de la Junta proposem les fusions possibles de TE, PAUL i SEM, cada una amb el que estalvia (hores de docent i hores d'aula), i una versió del 5.2 que les aplica, declarant R4-AULA i R4-DOCENT amb el motiu «classe fusionada».

Dades de les teories al 2n semestre:

- 964 grups ja són una sola classe compartida entre titulacions (`id_compartida`).
- Només 14 assignatures tenen més d'un grup de teoria amb aula. La majoria són de GEI o GEET+GEST de 1r i 2n, que no es toquen, o no caben juntes (l'aula més gran és de 160 places).
- Hi ha dos casos reals:
  - *Assignatura Inventada A*: el docent D951 la fa tres cops (GEI 3r TE/910 i TE/911, que sumen 148 alumnes, i GEQ 4t TE/908).
  - *900000* (GEET+GEST 3r): TE/909 i TE/913, amb 108 alumnes.
- Els PAUL i els SEM amb el mateix docent estan per calcular.

## 5.3 Imprevistos: canviar el mínim

Partim del 5.2 i només toquem les sessions afectades. Per a cada una, l'ordre de preferència és: la mateixa franja en una aula del mateix passadís; després, la mateixa franja en una altra aula; i un altre dia només per a la sessió cancel·lada. Cap sessió no canvia de torn.

- **Q9/5015 reservada del 15 al 19 de març.** Hi ha 12 sessions a recol·locar, només aquella setmana.
- **TE/908 de GEQ passa de 91 a 130 alumnes.** Com que és tot el semestre, la canviem a una aula de 130 o més a la mateixa franja, totes les setmanes. Si no n'hi ha cap de lliure, la desdoblem i declarem R3-AFORAMENT.
- **Q9/5004 avariada el 10 de març.** Recol·loquem les sessions d'aquell dia.
- **S95001, cancel·lada el 8 de març.** Es recupera fins al 19 de març, al torn del seu grup, en una franja amb l'alumnat, el docent i una aula lliures.

Es mesura amb `canvis_franja_vs_referencia` i `canvis_aula_vs_referencia`. Com menys canvis, millor.

## 5.4 Grau nou de 40 places

Les 235 sessions del grau nou ja són al matí, sense aula i sense fixar. Les col·loquem sobre el 5.2 amb la mateixa rutina i les mateixes regles, sense desdoblaments. Primer provem sense moure cap sessió del 5.2; si cal moure'n, el mínim, i diem quines. Si no hi cap, diem quina restricció ho impedeix, on, i el canvi més petit que ho faria possible (quantes aules de quina mida, o quina regla caldria relaxar). Qualsevol «no hi cap» es demostra amb un recompte o un INFEASIBLE.

## Com sabem que està fet

No n'hi ha prou que el subagent digui que està fet. Una ordre (`python -m nivell2.comprova <proposta>`) treu aquesta taula, abans (partida) i després:

| Què mirem | D'on surt |
|---|---|
| Veredicte i incompliments per codi | verificador (`avalua`) |
| Relaxacions declarades, per tipus i motiu | nostre |
| Activitats amb el mateix dia, hora i aula totes les setmanes (%) | nostre |
| Sessions que canvien de torn, i que cap no hi va sense que la regla 1 ho demani | nostre |
| Aules diferents per grup i setmana (mitjana i pitjor cas) | nostre |
| Hores mortes (`hores_mortes_min`) | verificador |
| Canvis d'aula entre classes seguides (`desplacaments_aula`, `desplacaments_edifici`) | verificador |
| Aula base (`r6_aules_te_extra_per_grup`, `r6_canvis_te_paul_fora_passadis`) | verificador |
| Canvis respecte d'avui (`canvis_franja`, `canvis_aula`) | verificador |

Si una xifra empitjora, es diu per què. Partim de les xifres del nivell 1 (pic de 15 de 19, ocupació del 68 %, cap llindar de mida falla al matí).

## Comparar titulacions amb justícia

Passa com amb les enquestes: qui té més temps sempre contesta més, i comparar-ho en absolut no és just. Una titulació gran sempre tindrà més sessions mogudes que una de petita. Per això:

- la xifra principal és el **percentatge de les seves sessions** que canvien (de franja, d'aula o de torn);
- no fem cap rànquing amb números absoluts; si en mostrem un, va al costat del percentatge;
- mirem el pitjor cas per titulació, no només el total, perquè cap titulació petita no pagui sola els canvis.

## Resum per a la Junta (una pàgina)

- El pic de classes alhora al matí i a la tarda, contra les aules ordinàries disponibles.
- Les aules que falten o que sobren, per mida.
- Les sessions mogudes per titulació i curs, en percentatge.
- Les excepcions a la regla 1, cadascuna amb el motiu i la prova.
- Alternativa: els desdoblaments de PAUL i SEM possibles, i les hores d'aula mitjana que alliberarien.
- Les fusions proposades, amb el que estalvien.

Format per defecte: una pàgina a l'app i el mateix en PDF. *(L'equip no ho ha triat.)*

## Visualització

Comença quan el disseny del nivell 1 estigui confirmat.

- **Primer, la vista per grup** (la de l'estudiant): l'horari de la setmana d'un grup, avui i proposta costat per costat, amb els canvis marcats.
- **Després, la vista per aula** (la que demana l'enunciat): una setmana tipus, dies en columnes i franges de 30 minuts en files, amb selector d'aula. Si hi ha l'alternativa amb desdoblaments, n'ensenya també la 2a hora.
- Selector de proposta (avui, 5.1, 5.2, 5.3, 5.4 i, si n'hi ha, les alternatives amb desdoblaments o fusions) i de setmana (per a les setmanes de l'imprevist).
- Es marquen les sessions amb relaxació i el seu motiu.
- La graella per aula també es lliura en un fitxer (HTML o PDF) per al jurat.

## Com treballem

- Solver OR-Tools CP-SAT: primer el dia i l'hora per activitat, després les aules. La integració instal·la `ortools` abans, perquè els subagents no tenen xarxa.
- Per a cada pregunta, primer una proposta vàlida i desada. Després es millora amb un límit de temps del solver, i sempre guardem la millor.
- Rols i ordre:
  1. **Backend:** el model, la rutina i el 5.1.
  2. **Dades:** `nivell2.comprova`, la comparació per titulacions i el càlcul de fusions.
  3. **Backend:** el 5.2, després el 5.3 i el 5.4. Els desdoblaments i les fusions, al final i només si sobra temps.
  4. **Dades:** el resum de la Junta.
  5. **Frontend:** la graella, quan el disseny del nivell 1 estigui confirmat.

## Quan està fet

- Cada pregunta té la seva proposta, l'informe del verificador, les relaxacions declarades, la taula de xifres i una mini demo d'un minut.
- `nivell2.comprova` diu que cap sessió no canvia de torn sense que la regla 1 ho demani .
- El resum de la Junta és d'una pàgina, amb les comparacions en percentatge.
- L'app mostra la vista per grup i la vista per aula, i la graella per aula també és en un fitxer.

## Pendent de confirmar

1. El format del resum de la Junta (ara per defecte: una pàgina a l'app i el mateix en PDF).

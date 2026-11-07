# Especificació de la part 2 · Proposta d'horari

> **Estat.** Afinada amb l'equip (entrevistes del ds 7-11, matí i tarda). No es programa ni es publica res fins que l'equip doni l'OK.
> La graella fa servir el disseny confirmat del nivell 1: B1, semàfor amb la resposta en gran (`docs/disseny/opcio-b1-resposta-gran.html`).

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

1. **5.1 Aules (5 %).** Amb l'horari d'avui, sense moure cap dia ni cap hora, donem aula a les 4.541 sessions que no en tenen. Es comprova amb `--nomes-aules`. Primer ha de ser VALIDA amb `--nomes-aules`: també es corregeixen les 43 sessions amb més alumnes que places i les 54 de tipus d'aula equivocat. Després es premia que sigui bona: aula base per grup, pocs canvis d'aula entre classes seguides i pocs canvis respecte de l'aula d'avui.
2. **5.2 Torns nous (25 %).** Cada sessió va al torn que li toca segons la regla 1, i diem què costa. Hi afegim el resum de la Junta.
3. **5.3 Imprevist (10 %).** Partim del 5.2 i resolem quatre imprevistos alhora, canviant el mínim.
4. **5.4 Grau nou de 40 places (10 %).** Col·loquem les 235 sessions del 2n semestre sobre el 5.2.

I, un sol cop, la graella setmanal per aula de la proposta més avançada.

## Regles que ens posem (a més del verificador)

Les regles són per ordre de prioritat. Quan dues xoquen, guanya la primera.

1. **Les regles del verificador.** Cap relaxació en silenci: totes es declaren amb el motiu.
2. **La rutina és una prioritat forta, no una regla dura** (decisió del ds 16:25). Planifiquem per activitat (`activitat_id`), no per sessió. Primer intentem que totes les sessions d'una activitat vagin al mateix dia, la mateixa hora i la mateixa aula totes les setmanes. Si el calendari (festius, aturades, avaluació) o una setmana concreta ho impedeixen, s'hi admeten excepcions puntuals: cada una es compta a la taula de xifres i s'explica. La rutina mai no passa per davant del verificador.
3. **El torn de l'estudiant.** Al 5.1, al 5.3 i al 5.4 cap sessió no canvia de torn. Al 5.2 una sessió només canvia de torn si la regla 1 l'hi obliga. Mai no es mou cap a l'altre torn una sessió que ja és al seu.
4. **Mínims canvis respecte d'avui.** Un canvi d'hora o de dia pesa més que un canvi d'aula (pesos a «Detalls per programar»). Quan una sessió s'ha de moure, primer es prova el mateix dia; només va a un altre dia si no hi cap o si el cost total baixa. La rutina (2) va davant dels mínims canvis (decisió del ds 7-11, tarda).
5. **Aula base i passadís.** La teoria i els problemes d'un grup, a la mateixa aula o al mateix passadís (mateixa espina i planta).
6. **Poques hores mortes.** Les classes mogudes s'enganxen a les altres del grup aquell dia.

## Detalls per programar

Decisions de l'equip del ds 7-11 a la tarda. Són el que un subagent necessita per escriure el model sense suposar res.

### Paraules

- **Sessió:** una classe en una data (`id_sessio`). És la fila de la proposta.
- **Activitat** (`activitat_id`): les sessions d'un mateix grup, dia i hora al llarg del semestre. És la unitat que planifiquem.
- **Grup d'estudiants:** cohort (titulació i curs, `GED:1r`) i línia (els primers dígits del grup: TE/81, PAUL/811 i PAUL/812 (inventats) són la línia 8). És el mateix que fa servir el verificador per a l'aula base i les hores mortes.
- **TE** teoria · **PAUL** problemes d'aula (subgrups de la teoria) · **SEM** seminari · **PLAB** laboratori (no es toca).
- **Franja:** una hora d'inici possible (vegeu «Hores d'inici»). La reserva de dues aules (R8) es compta per franges d'**una hora** (8.30, 9.30 … 20.30), com fa el verificador.
- **Passadís:** mateixa espina i planta (Q9/0101 i Q9/0102 (inventades) són al mateix passadís).
- **CP-SAT:** el solver de restriccions d'OR-Tools. Acaba amb un d'aquests estats: OPTIMAL (el millor possible), FEASIBLE (n'ha trobat una de bona), INFEASIBLE (ha demostrat que no n'hi ha cap) o UNKNOWN (no ha acabat a temps; no vol dir que sigui impossible).

### Pesos del solver

El solver minimitza la suma d'aquests costos. Són constants en un sol lloc del codi, perquè es puguin canviar.

| Què | Cost |
|---|---:|
| Una sessió canvia de dia o d'hora respecte d'avui | 10 |
| Una sessió canvia d'aula respecte d'avui (si avui en tenia) | 3 |
| Un canvi d'aula entre dues classes seguides d'un grup fora del mateix passadís | 2 |
| Cada 30 minuts d'hora morta d'un grup | 1 |

La rutina va per davant: una activitat que trenca la rutina en una setmana es compta a part, i el solver ho evita abans que tota la resta.

### Hores d'inici

- Una classe pot començar **cada mitja hora**: 8.30, 9.00, 9.30 … sempre que acabi dins la finestra del seu torn (matí 8.30-14.30, tarda 14.30-21.00).
- Les 22 sessions que avui comencen a i quart es queden a la seva hora si no s'han de moure; si es mouen, van a una hora en punt o a i mitja.

### Festius i setmanes diferents

- Els candidats de dia es generen per **data real** (calendari, festius, no lectius, aturades, avaluació).
- Si una activitat es mou a un dia que alguna setmana és festiu o no lectiu, la sessió d'aquella setmana va a un altre dia lliure de la mateixa setmana i del mateix torn. Compta com a excepció de rutina i s'explica a les xifres.

### Alumnes dels grups sense dada

Ja resolt (commit `e956847`): el model llegeix `dades/alumnes_sense_dada.json` (vegeu «Riscos tècnics»).

### Aules d'altres centres

- Les 35 sessions que avui es fan a **B3/0021** s'hi queden si no canvien de franja. Si el solver les mou de franja, van a l'aulari. No s'hi porta cap sessió nova.
- Cap sessió del 2n semestre no és avui a les aules J.

### De nit i de dia

- **De nit** (quan no ho fa servir ningú) es fa el càlcul llarg: el 5.2 sencer i les millores. Primer una proposta vàlida i desada, després la millora amb el temps que calgui. Cada proposta bona es desa de seguida.
- **De dia**, un canvi petit (un imprevist, afegir o moure una classe) triga **menys d'1 minut**. Es fa amb **reparació local**: es parteix de l'horari de nit, es fixen totes les sessions i només es deixen moure les afectades. Si no hi ha solució, s'amplia el cercle pas a pas: les que comparteixen grup, docent o aula; després, el mateix dia; després, la setmana.
- La reparació és una funció, `repara(proposta, canvi)`, que fan servir el 5.3 i, després, l'assistent del nivell 3. A l'app només hi va si sobra temps.

### Vista de l'estudiant

- Titulació → curs → grup d'estudiants (GED → 1r → 81). Si un camp només té una opció, s'explica com a dada i no es mostra com a selector. «Grup d'estudiants» són els alumnes que comparteixen la teoria i els subgrups de problemes i seminaris; s'explica també què vol dir que coincideixin subgrups.
- La graella ensenya la setmana de l'estudiant: la teoria del grup i els seus problemes i seminaris (81, 811, 812…).
- Es poden consultar tots els cursos i tot el dia (8.30–21.00). Primer és la selecció inicial, no un filtre del conjunt de dades.

### Propostes i dades fora de git

- Res que surti de les dades del repte no va a git: ni les propostes (`resultats/`), ni les xifres per grup (`dades/`), ni els CSV. El `.gitignore` les ignora.
- Les propostes es queden al Mac, a `resultats/nivell2/<apartat>/`, i es poden tornar a generar amb l'ordre del `README.md` de cada carpeta. Al jurat se li lliuren directament, no per GitHub.

## 5.2: què es pot moure

- Es pot moure el dia, l'hora i l'aula de **qualsevol sessió movible**, no només de les que són fora de torn. Cada canvi té un cost, i el solver només mou una sessió que ja era bé si hi guanya prou (fer-hi cabre les altres, l'aula base, menys hores mortes).
- No es toquen les de GEI i GEET+GEST de 1r i 2n ni els PLAB. Una sessió no canvia ni de setmana ni de durada.
- Avui hi ha 2.008 sessions al torn equivocat (R1-TORN). Unes 246 movibles de 1r i 2n són a la tarda i passen al matí. El gruix, unes 1.770 de 3r, 4t, dobles i màsters, és al matí i passa a la tarda.
- **El torn no el triem nosaltres.** El fixa la regla 1 (línies mestres de la Direcció): 1r i 2n al matí (8.30-14.30); 3r, 4t, dobles i màsters a la tarda (14.30-21.00). El verificador ho comprova (R1-TORN). Nosaltres triem el dia, l'hora i l'aula dins del torn de cada sessió, canviant el mínim.
- **Hi cap a tots dos torns (comprovat el ds 16:40, balanç d'hores d'aula de l'aulari a la pitjor setmana, sense PLAB ni dobles):**
  - **Matí:** 397 h contra 570 h (19 aules × 6 h × 5 dies), el 70 %. És el torn ajustat.
  - **Tarda:** passa de 105 h (les que avui ja hi són) a 259 h, perquè hi arriben 1.526 sessions de 3r i 4t que avui són al matí (+154 h). Contra 570 h (19 aules × 6 h de 15 a 21 h × 5 dies) és el 45 %. Per mida d'aula no falla cap llindar.
  - Per tant, no esperem cap excepció a la regla 1. És una condició necessària: no prova que l'horari encaixi sense solapaments de docent i alumnat. Això ho diu el solver.
- **Excepcions a la regla 1, només si és impossible.** Ho demostrem amb un recompte (demanda contra oferta per franja i mida d'aula) o amb un INFEASIBLE del solver que no relaxi res. Si només és «no l'hem trobat», ho diem així. Una sessió amb excepció es queda al torn d'avui.
- El 5.2 no deixa lloc per al grau nou: és el 5.4 qui s'hi adapta.
- No calculem alternatives de torn: només la regla 1 tal qual.

## Alternativa per a la Junta: desdoblament per rotació (PAUL i SEM)

> **Decisió (ds 16:20).** El desdoblament **no va a les propostes lliurades** (5.1-5.4). Obligaria a declarar R3-AFORAMENT a unes 1.197 sessions (153 activitats), i qualsevol proposta VALIDA sense relaxacions passaria per davant. El verificador del jurat tampoc no veu la meitat B. A més, no cal: al nivell 1 cap mida d'aula falla al matí. Es fa com a alternativa per a la Junta, i només quan els quatre lliuraments estiguin fets i validats.

**Com seria:** tot grup de problemes (PAUL) o de seminari (SEM) movible de **més de 34 alumnes** es parteix en dues meitats. L'aula petita és un seminari o una aula de fins a 34 places, totes de fins a 34 places. Un grup que hi cap sencer (34 alumnes o menys) no es parteix. **Sempre en dues meitats, mai en més parts:** un grup de 100 es parteix en dues meitats de 50, no en quatre de 25. Cada meitat va a l'aula més petita on hi càpiga (una meitat de 50 va a una aula de 48-50 o de 63). La teoria (TE) no es parteix.

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
| 1–34 | 9: 8 seminaris (10–34) i una aula de 24 | 23 | 82 | 0 |
| 35–50 | 4 aules de 35 a 50 places | 16 | 101 | 6 |
| 51–63 | 2 aules | 20 | 25 | 4 |
| 64–90 | 7 aules de 64 a 90 places | 51 | 4 | 0 |
| 91–160 | 7: dues de 100, dues de 117, dues de 130 i una de 160 | 14 | 1 | 0 |

(Hi ha 14 grups sense dada d'alumnes al paquet; ara tenen xifra, vegeu «Grups sense dada d'alumnes». Comptem els grups del 2n semestre un cop cadascun, sense PLAB ni dobles.)

**Per què ho fem:** hi ha 101 grups de problemes de 35 a 50 alumnes, i només 4 aules d'aquesta mida. Avui ocupen aules de 63 o de 90 places, que són les que necessita la teoria. Partits en meitats, caben en un seminari i alliberen les aules mitjanes. Cada desdoblament compta com a canvi a la taula de xifres, i la Junta veu quants n'hem fet i quantes hores d'aula mitjana alliberen.

> Per comprovar en programar: 8 seminaris i l’aula de 24 potser no basten per a totes les meitats a l'hora punta. Si no hi caben, la meitat va a la següent aula més petita lliure, i ho comptem.

## Fusió de classes amb el mateix docent (proposta per a la Junta)

No té sentit que un docent faci dues vegades la mateixa classe a grups que hi caben junts. El 5.2 es lliura **sense fusions** (vàlid net). Al resum de la Junta proposem les fusions possibles de TE, PAUL i SEM, cada una amb el que estalvia (hores de docent i hores d'aula), i una versió del 5.2 que les aplica, declarant R4-AULA i R4-DOCENT amb el motiu «classe fusionada».

Dades de les teories al 2n semestre:

- 964 grups ja són una sola classe compartida entre titulacions (`id_compartida`).
- Només 14 assignatures tenen més d'un grup de teoria amb aula. La majoria són de GEI o GEET+GEST de 1r i 2n, que no es toquen, o no caben juntes (l'aula més gran és de 160 places).
- Hi ha dos casos reals:
  - Una assignatura de 3r i 4t que el mateix docent fa tres cops: dos grups de teoria d’una titulació (148 alumnes en total) i un d’una altra.
  - Una assignatura compartida per dues titulacions de 3r: dos grups de teoria amb 108 alumnes.
- Els PAUL i els SEM amb el mateix docent estan per calcular.

## 5.3 Imprevistos: canviar el mínim

Partim del CSV final del 5.2, que no es toca, i només toquem les sessions afectades. Les afectades es calculen sobre aquest 5.2, no sobre l'horari d'avui (les 12 de l’aula reservada són d'avui i poden canviar). Si amb les afectades no n'hi ha prou, se n'amplien de mica en mica les que es poden moure. Per a cada una, l'ordre de preferència és: la mateixa franja en una aula del mateix passadís; després, la mateixa franja en una altra aula; i un altre dia només per a la sessió cancel·lada. Cap sessió no canvia de torn.

- **Una aula reservada del 15 al 19 de març.** Hi ha 12 sessions a recol·locar, només aquella setmana.
- **Un grup de teoria de GEQ passa de 91 a 130 alumnes.** Com que és tot el semestre, la canviem a una aula de 130 o més a la mateixa franja, totes les setmanes. Si no n'hi ha cap de lliure, la desdoblem i declarem R3-AFORAMENT.
- **Una aula avariada el 10 de març.** Recol·loquem les sessions d'aquell dia.
- **Una sessió cancel·lada el 8 de març.** Es recupera fins al 19 de març, al torn del seu grup, en una franja amb l'alumnat, el docent i una aula lliures.

Es mesura amb `canvis_franja_vs_referencia` i `canvis_aula_vs_referencia`. Com menys canvis, millor.

## 5.4 Grau nou de 40 places

Les 235 sessions del grau nou ja són al matí, sense aula i sense fixar. Les col·loquem sobre el 5.2 amb la mateixa rutina i les mateixes regles, sense desdoblaments. Primer provem sense moure cap sessió del 5.2; si cal moure'n, el mínim, i diem quines. Si no hi cap, diem quina restricció ho impedeix, on, i el canvi més petit que ho faria possible (quantes aules de quina mida, o quina regla caldria relaxar). Qualsevol «no hi cap» es demostra amb un recompte o un INFEASIBLE.

La resposta és sempre una d'aquestes quatre, i es diu quina (decisió del ds 16:25):

1. **Hi cap**, amb una proposta que el verificador dona per bona.
2. **No hi cap sense tocar el 5.2**, en les condicions provades (rutina, 5.2 congelat). Això no prova que sigui impossible.
3. **No l'hem trobat** dins del temps disponible. Un UNKNOWN del solver vol dir això, no que sigui impossible.
4. **Hem demostrat que no existeix** amb unes regles explícites. Per demostrar-ho cal un recompte (demanda superior a l'oferta màxima defensable en dates, franges i mides concretes) o un INFEASIBLE d'un model complet, sense rutina obligatòria ni el 5.2 congelat.

Si és el 4, diem el coll d'ampolla i el canvi que el resol. Parlem de «canvi mínim» només si hem demostrat que és el mínim; si no, diem «el canvi més petit que hem trobat».

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

Format: una pàgina a l'app i el mateix exportat a PDF.

## Visualització

Fa servir el disseny B1 del nivell 1, amb textos planers per al tècnic de Gestió Acadèmica. El frontend pot començar amb dades de mostra, sense esperar el solver.

- **Primer, la vista per grup** (la de l'estudiant): «Horari actual · dades originals» i «Amb la proposta» costat per costat si hi ha prou espai, o apilats en pantalles petites. «Només l'horari actual» mostra una única graella; no compara les dades originals amb elles mateixes.
- **Després, la vista per aula** (la que demana l'enunciat): una setmana tipus, dies en columnes i franges de 30 minuts en files, amb selector d'aula. Si hi ha l'alternativa amb desdoblaments, n'ensenya també la 2a hora.
- Les propostes disponibles s'anomenen amb la millora que fan, a més del número (5.1 assignar aules sense moure dies ni hores, 5.2 reorganitzar torns, etc.). Si només n'hi ha una, no cal un selector. La setmana seleccionada afecta les dues vistes i la vista per aula.
- «Aula no indicada a les dades» explica una mancança dels fitxers originals, no que una classe no es faci. Es compten i s'expliquen aquestes mancances per al grup seleccionat.
- Llegenda visible amb text: blau sense canvis, verd aula afegida, groc dia/hora/aula existent modificats, vora discontínua cas especial amb motiu. Els canvis també s'escriuen dins de la classe. TE/PAUL/SEM es tradueixen i els grups es mostren en paraules.
- Ajuda opcional «Com funciona? Guia pas a pas»: sis passos que expliquen la comparació, els estudiants, les mancances d'aula, els colors, les graelles i la vista per aula. Cada pas porta al seu apartat; es pot retrocedir, acabar o tancar la guia.
- Es marquen les sessions amb relaxació i el seu motiu.
- La graella per aula també es lliura en un fitxer (HTML o PDF) per al jurat.
- **Setmana seguida (petició de Bernat):** una sola graella de dilluns a divendres inclòs, també a la vista per aula i a l'HTML descarregat. No es parteix en blocs de dies ni en taules de carrils. Si falta amplada, es desplaça lateralment la mateixa graella, mantenint les hores a la vista i una amplada llegible per classe.
- Les tres xifres del resum (canvis d’hora, canvis d’aula i aules a la setmana) van en columnes iguals, centrades amb les etiquetes, tant en escriptori com en mòbil.

## Com triem la millor proposta

És l'ordre del jurat (apartat 7 de l'enunciat):

1. **VALIDA** sense relaxacions.
2. **VALIDA AMB RELAXACIONS DECLARADES**, amb menys `incompliments_declarats` i justificacions que s'aguantin.
3. Dins del mateix grup, millors objectius (hores mortes, desplaçaments i canvis) i més rutina.

El veredicte es llegeix del JSON del verificador, no del codi de sortida: el codi 0 també surt amb relaxacions. R3-TANCADA i R5-RECUPERACIO no es poden relaxar.

## Riscos tècnics i com els evitem

- **Calendari:** els candidats de dia i hora es generen per **data real**: festius, no lectius, aturades, setmanes d'avaluació i dies sense classes a la partida. Totes les sessions d'una activitat es comproven, no només la primera.
- **Reserva R8:** el verificador compta les **aules diferents ocupades dins de cada franja d'una hora** (8.30, 9.30… 20.30). No n'hi ha prou de limitar a 19 classes simultànies cada mitja hora. Cal reproduir aquest recompte exacte.
- **Sessions compartides** (`id_compartida`): són una sola classe física. Es mouen juntes, a la mateixa aula, amb els alumnes **sumats** i tots els docents i cohorts.
- **Grups sense dada d'alumnes** (decisió ds 7-11): al 2n semestre, 14 grups (276 sessions, sense PLAB ni dobles) tenen `alumnes = 0`. El model llegeix un fitxer local de `dades/` (fora de git) i posa aquella xifra a totes les sessions del grup (codi + grup): matriculats del portal públic SIQ de la UAB per a dues optatives, o una estimació amb el mateix paquet per a la resta. Els grups que són la mateixa classe que uns altres (compartides) es queden a 0, perquè les compartides sumen els alumnes. El verificador oficial continua veient-hi 0, i per tant no hi comprova l'aforament: la xifra només serveix perquè el nostre model triï una aula on hi càpiguen.
- **Sense espai** (dobles, `sense_espai = 1`): no necessiten aula, però sí que compten per al torn, el docent i l'alumnat.
- **R4-PLAB:** els PLAB són obstacles fixos. Una TE o un PAUL de la mateixa assignatura no hi pot coincidir.
- **Heretats:** els conflictes que ja hi són avui i que el verificador marca com a heretats no s'han de prohibir al model, perquè llavors no hi hauria solució. Cal distingir-los dels nous.
- **El solver no acaba:** límit de temps per fase, guardar sempre la millor proposta que el verificador dona per bona i registrar l'estat del solver (OPTIMAL, FEASIBLE, INFEASIBLE o UNKNOWN). UNKNOWN no vol dir impossible.

## Contracte de lliurament

Cada pregunta té la seva carpeta, `resultats/nivell2/<5.1|5.2|5.3|5.4>/`, amb:

- `proposta.csv`;
- `informe.json` i `violacions.csv`;
- `relaxacions.csv`, només si n'hi ha;
- `xifres.csv`, la taula abans i després;
- `README.md` amb l'ordre exacta per generar-la i per verificar-la (llavor i límit de temps del solver inclosos).

Abans d'empaquetar, es tornen a executar les quatre ordres del verificador sobre els fitxers finals. `resultats/` no conté dades del paquet, només les propostes (identificadors de sessió, dia, hora i aula).

## Temps

L'entrega és diumenge a les 12:00, i a les 2:00 es congela el codi. L'ordre és:

1. 5.1 VALIDA.
2. 5.2 VALIDA.
3. 5.3 i 5.4, en paral·lel, sobre el 5.2 congelat.
4. Resum de la Junta i graella.
5. Millores amb el temps que quedi.
6. Alternatives (desdoblaments i fusions), només si sobra temps.

## Com treballem

- Solver OR-Tools CP-SAT: primer el dia i l'hora per activitat, després les aules. La integració instal·la `ortools` abans, perquè els subagents no tenen xarxa.
- Per a cada pregunta, primer una proposta vàlida i desada. Després es millora amb un límit de temps del solver, i sempre guardem la millor.
- Rols i ordre:
  1. **Backend:** el model, la rutina i el 5.1.
  2. **Dades:** `nivell2.comprova`, la comparació per titulacions i el càlcul de fusions.
  3. **Backend:** el 5.2, després el 5.3 i el 5.4. Els desdoblaments i les fusions, al final i només si sobra temps.
  4. **Dades:** el resum de la Junta.
  5. **Frontend:** la graella i el resum de la Junta a l'app, des del principi i amb dades de mostra.

## Quan està fet

- Cada pregunta té la seva proposta, l'informe del verificador, les relaxacions declarades, la taula de xifres i una mini demo d'un minut.
- `nivell2.comprova` diu que cap sessió no canvia de torn sense que la regla 1 ho demani .
- El resum de la Junta és d'una pàgina, amb les comparacions en percentatge.
- L'app mostra la vista per grup i la vista per aula, i la graella per aula també és en un fitxer.

## Pendent de confirmar

Res. L'especificació està a punt per a l'OK de l'equip.

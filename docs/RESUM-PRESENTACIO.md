# Base per a la presentació · Horaris i espais

Guió en català planer. Cada apartat proposa una diapositiva. Les xifres de les propostes finals del nivell 2 estan contrastades amb els informes agregats de `resultats/nivell2/`. Els balanços d’hores i les comprovacions de la part 1 surten del diari (16:30 i 17:19); els grups sense nombre d’alumnes i les sessions afectades, de l’entrada de les 17:40. La història de la revisió surt del diari i de `docs/REVISIO-PUNT5.md`.

## El problema i les persones

- Gestió Acadèmica necessita fer i mantenir un horari que encaixi; coordinació i Junta han de poder decidir amb un resum clar.
- L'estudiant necessita una setmana previsible: mateix dia, hora i aula, amb poques hores mortes.
- El punt de partida té 2.008 sessions fora del torn que els correspon i 4.541 pendents d'assignar aula.
- També hi ha 43 sessions amb més alumnes que places: disposar d'hores lliures no garanteix trobar l'aula adequada.

Nota per a qui presenta: són recomptes del semestre, no d'una sola setmana. Font: [diari](DIARI.md), entrades de les 13:24 i 17:19; [especificació](../.plans/nivell2-horari-spec.md), «Què lliurem»; persona definida al diari a les 16:01. No confondre manca d'aula a les dades amb classe cancel·lada.

## Part 1 · Entendre com estem avui

- Una app local respon les preguntes de Gestió Acadèmica amb xifres, gràfics senzills i una explicació del càlcul.
- La diagnosi distingeix setmana habitual, pitjor setmana, matí i tarda.
- Amb els torns nous, el balanç del matí demana 397 hores d'aula davant de 570 disponibles; la tarda, 259 davant de 570.
- Les 25 de 25 comprovacions de la diagnosi quadren; el balanç d'hores és una pista de cabuda, no una prova d'horari viable.

Nota per a qui presenta: el pic del matí queda igual, 15 de 19 aules, tant a l’horari inicial com al 5.2. El que canvia és la tarda: el 5.2 final queda a 18 de 19. Fonts: diari, 13:24, per al pic inicial; `resultats/nivell2/junta/5.2/junta.json`, per als pics finals. Els balanços 397/570 i 259/570 surten del diari, 16:30; les 25 de 25 comprovacions, de les 17:19. La part 1 comprova la diagnosi; les propostes de la part 2 passen pel verificador oficial.

## Part 2 · Propostes comprovades

- **5.1 · Aules:** assignar espais sense canviar dies ni hores. Veredicte oficial: **VALIDA**, sense relaxacions, amb la comprovació d'aules.
- **5.2 · Horari complet:** reorganitzar els torns, assignar aules i prioritzar la rutina. Veredicte: **VALIDA AMB RELAXACIONS DECLARADES**.
- **5.3 · Imprevistos:** reparar l'horari del 5.2 canviant el mínim. Veredicte: **VALIDA AMB RELAXACIONS DECLARADES**.
- **5.4 · Grau nou:** hi caben les 235 sessions d'un grau de 40 places sense moure cap sessió del 5.2 i amb rutina setmanal per a les activitats noves. Veredicte: **VALIDA AMB RELAXACIONS DECLARADES**.
- Totes passen el verificador oficial; la comprovació complementària de persones dona **CORRECTE** al 5.2 i als escenaris del 5.3 i el 5.4.

Nota per a qui presenta: una relaxació és una excepció declarada amb motiu, no una regla ignorada. No presentar totes les propostes com a vàlides sense excepcions. Font: diari, 18:02, 21:25 i 21:55. Els veredictes s'han contrastat amb els `informe.json` finals.

## Xifres finals · Què guanyem i què costa

- **5.1:** 369 canvis d'aula i cap canvi de franja. Les aules de teoria addicionals per grup passen de 14 a 9 segons el verificador. Sense els dobles que no necessiten espai propi, passen de 8 a 9: aquest indicador empitjora.
- **5.2:** 459 excepcions de torn: 458 classes de 1r i 2n fixades que ja són a la tarda i que la regla 1 impedeix moure, més 1 excepció nova, demostrada, de la setmana d'avaluació. Hi ha 2.015 sessions que canvien de franja (2.007 canvien de torn per la regla 1 i 8 canvien d’hora dins el mateix torn).
- Respecte de l'horari inicial, les hores mortes passen de 72.930 a 107.100 minuts. Els desplaçaments d'aula passen de 544 a 1.420 i els d’edifici, de 0 a 17. Hi ha 2.015 canvis de franja respecte de l’horari inicial. Reorganitzar torns i assignar les aules que faltaven té aquest cost.
- Les aules de teoria addicionals per grup passen de 14 a 3 en el recompte oficial. El 95,60 % de les activitats manté dia, hora i aula cada setmana; hi ha 36 sessions fora del patró habitual, amb el motiu documentat a `resultats/nivell2/5.2/excepcions.csv`.
- **5.3:** 65 classes canvien d'aula al CSV respecte del 5.2; el verificador en compta 64 perquè exclou la cancel·lada. Dels 64 canvis d’aula oficials, 52 corresponen a les afectades pels imprevistos, sense comptar la cancel·lada, i 12 a classes de suport. Hi ha 10 classes fixades que canvien d’aula perquè la seva està tancada: 8 R1-FIXADA i 2 R7-PLAB. Hi ha 1 canvi de franja: només la cancel·lada canvia de dia. Cap classe canvia de torn. S’afegeixen 10 excepcions a les 459 del 5.2, fins a 469. La reserva mínima operativa és de 2 aules i les hores mortes queden en 106.860 minuts. El resultat és òptim per al veïnat obert del model de reparació, no per al problema global.
- **5.4:** hi caben les 235 sessions noves del grau de 40 places. Se'n mouen 41 de la franja original. Les hores mortes del grau nou són 1.620 minuts: el total passa de 107.100 a 108.720. Els desplaçaments d’aula passen de 1.420 a 1.461 i les aules de teoria addicionals, de 3 a 4. Es mouen 0 classes del 5.2 i es creen 0 conflictes nous d'alumnat i 0 de professorat.

Nota per a qui presenta: fonts finals: `5.1/README.md`, els `xifres.csv`, els `resum.json` i els `informe.json` de `resultats/nivell2/`. Al 5.1 no hi ha `resum.json`. Les 12 classes de suport del 5.3 s'han recomptat comparant les propostes amb les sessions afectades que identifica el codi de reparació. No confondre canvi d'una aula ja assignada amb assignació d'una aula que faltava.

## Marge d'aules · Encaixar no és suficient

- Al 5.2, el pic del matí queda igual que a l’horari inicial: 15 de 19 aules ordinàries disponibles. A la tarda és de 18 de 19: queda una aula de marge en aquest recompte.
- Aquest pic compta aules diferents ocupades dins d'una hora. El màxim de classes simultànies és 15 al matí i 18 a la tarda; el pic d’aules de la setmana típica a la tarda és 17 de 19.
- Es guarden 2 aules de reserva. La mida de les aules també limita el marge útil.
- Recomanem deixar 1–2 aules lliures a l'hora punta per afrontar avaries i grups que creixen.

Nota per a qui presenta: font: `resultats/nivell2/junta/5.2/junta.json`, camps `pics` i `aulari`. Ja no correspon dir que la tarda ocupa 19 de 19 ni que no té marge.

## Com sabem que és correcte

- En una segona revisió, 5 agents revisors van revisar cadascun la feina de dos subagents i van trobar i fer arreglar, entre altres coses, les hores mortes del grau nou que no es veien (3.420 → 1.620 minuts), 14 sessions que trencaven la rutina sense motiu i el resum A4 de la Junta que havia quedat antic.
- 12 revisors de Codex van revisar el punt 5. Tres per apartat: un contrastava l'enunciat, un revisava el codi i un recalculava els resultats.
- Van trobar errors que el verificador oficial no veu. El més greu eren 12 coincidències d'alumnat del grau nou: la teoria TE/91, de 40 alumnes, coincidia amb problemes PAUL/92, on va una part d'aquests mateixos alumnes.
- El verificador compara números de grup i no detectava aquesta relació entre 91 i 92. Hem fet explícit que la teoria de tot el grup inclou els subgrups. Només permetem problemes simultanis quan hi ha prou informació per separar l'alumnat.
- Hem tornat a calcular el 5.3 i el 5.4 sobre el 5.2 corregit. `comprova_persones` comprova l'alumnat, els dobles i ara també el professorat. Busca conflictes nous respecte de l'horari inicial; no afirma que hagin desaparegut tots els conflictes heretats.
- També s'ha impedit reutilitzar informes antics si falla la verificació. El resum de la Junta comprova l'empremta de la proposta i es recalcula si ha canviat.

Nota per a qui presenta: història documentada a [la revisió](REVISIO-PUNT5.md) i al [diari](DIARI.md), des de les 22:50. La comprovació pròpia complementa el verificador oficial. Els resultats finals del grau nou registren zero conflictes nous tant d'alumnat com de professorat.

## Coses del verificador que expliquem

- Compta com a desplaçament el pas entre dues classes que comencen alhora.
- Compta com a «aula extra» classes de dobles que no necessiten aula pròpia.
- No compta el canvi d'aula de la classe cancel·lada.

## Problema interessant · Els dobles graus

- Les dades no deien a quina classe assistien els estudiants dels dobles graus.
- La recerca a la web de la UAB i a siq.uab.cat va aclarir que tenen grup propi i també comparteixen classes amb graus simples.
- Vam lligar cada classe del doble a la classe on va: es mouen juntes i no es dupliquen ni necessiten una aula pròpia addicional.
- `nivell2/comprova_persones.py` comprova que no apareguin solapaments nous i que les classes lligades no se separin ni es dupliquin.

Nota per a qui presenta: l'equip executa aquesta comprovació; els agents només en reben recomptes i el veredicte. Les poques classes sense parella no es mouen. Font: diari, 20:58, 21:25 i 22:00. Les webs són les fonts de la recerca documentada, no s'han consultat de nou per fer aquest guió.

## Problema interessant · Les dades que faltaven

- Hi havia 14 grups sense nombre d'alumnes, que afectaven 276 sessions.
- Es van completar amb matriculacions públiques del SIQ o estimacions de la promoció; les classes compartides es tracten sense comptar alumnes dues vegades.
- Aquestes xifres ajuden el model a triar aules amb prou places; el verificador oficial continua veient la mancança original.
- «Aula no indicada» vol dir que falta l'assignació als fitxers, no que la classe no es faci.

Nota per a qui presenta: no atribuir al verificador una comprovació d'aforament que no pot fer quan li falta el nombre d'alumnes. Els complements es queden fora del repositori. Font dels 14 grups i les 276 sessions: diari, 17:40. Context: diari, 22:00; especificació, «Riscos tècnics».

## Problema interessant · Torns, calendari i rutina

- La regla 1 fixa els primers cursos al matí i els cursos superiors, dobles i màsters a la tarda; l'equip no tria lliurement el torn.
- La setmana d'avaluació concentra les classes que cal moure en massa poc temps: el calendari impedeix portar-les als altres dies.
- La solució admet excepcions puntuals al torn, declarades i justificades; també declara els casos de classes fixades que necessiten aula.
- La rutina és una prioritat forta: mateix dia, hora i aula cada setmana, amb excepcions de calendari comptades i explicades.
- Quan el model complet no acabava a temps, vam passar a reparació local: primer complir les regles i després millorar.

Nota per a qui presenta: un model que no acaba no demostra que no hi hagi solució. Les excepcions per impossibilitat requereixen recompte o prova del model. Font: diari, 16:24, 18:05, 18:12, 18:23 i 21:25; especificació, «5.2: què es pot moure».

## Norma de dades · Com treballem ara

- L’equip ha retirat la restricció de lectura anterior i ha autoritzat el contrast dels resultats finals per a aquesta revisió documental.
- El disseny i les proves visuals es verifiquen amb dades inventades.
- Durant la restricció, el codi comprovava les dades locals i als agents només els arribaven recomptes, errors sense valors reals i veredictes.
- Les dades i els resultats derivats queden fora del repositori; l'app és local.

Nota per a qui presenta: aquesta restricció es va aplicar des del vespre i l’equip l’ha retirat per a la revisió final. Abans, segons el permís inicial comunicat a l'equip, els agents sí que havien llegit dades. El README ho explica: la neteja posterior no desfà el contingut que ja havia passat pels serveis d'IA. Font: diari, 19:09 i 20:15; [README](../README.md), «Ús de les dades del repte, abans i després de la restricció».

## Ús de la IA · Repartiment i decisions humanes

- Claude orquestra: concreta especificacions, reparteix tasques, revisa i integra els resultats.
- Subagents de Codex amb `gpt-6.1-sol` treballen per rol: dades, backend i frontend, en worktrees separats i en paral·lel.
- L'equip decideix prioritats: rutina de l'estudiant, mínims canvis, excepcions explícites i alternatives fora del lliurament principal.
- Per triar el disseny: al migdia, maquetes HTML locals (A, B, C); al vespre, quatre propostes de graella fetes amb Claude Design. L'equip tria la forma de la B amb els colors per estat de la A.
- L'equip valida l'ús real; el verificador oficial i les comprovacions de persones contrasten el que produeixen els agents.

Nota per a qui presenta: les maquetes del migdia eren HTML locals; la graella final es va triar entre quatre propostes de Claude Design (dades inventades). Font: diari, 13:17, 13:52, 17:52, 19:30 i 21:55; README, «Ús d'IA».

## Què queda per fer · Explicar els límits

- Guanyar marge d'aules a l'hora punta: la validesa actual no resol la fragilitat operativa.
- **Fet:** comparació final del 5.2 contrastada: 72.930 → 107.100 minuts d’hores mortes i 95,60 % d’activitats amb rutina setmanal.
- Revisar les excepcions amb Gestió Acadèmica i la Junta, i explicar també qualsevol indicador que empitjori.
- Tornar a verificar els fitxers finals abans del lliurament i preparar la demo i el material de reserva.
- Com a evolució: consulta personal de l'estudiant, peticions del professorat i assistent; les fonts no acrediten que aquestes ampliacions estiguin acabades.

Nota per a qui presenta: les xifres finals ja estan contrastades amb els informes agregats. No prometre que s'ha trobat l'horari òptim: tenim propostes validades. Fonts: especificació, «Com sabem que està fet» i «Contracte de lliurament»; diari, 15:52, 16:01 i 22:00.

## Idees descartades

- **Mesurar seients buits:** no tenim assistència real; per dimensionar, suposem que hi va tot l'alumnat matriculat.
- **Comparar pla i realitat:** falta el fitxer de l'ús real dels espais al paquet.
- **Desdoblaments per rotació i fusions al lliurament principal:** es reserven com a alternatives per a la Junta; afegeixen excepcions i el verificador no veu tota la rotació.
- **Alternatives lliures de torn:** es deixa de proposar-les per seguir la regla 1 de la Direcció.
- **Mapes de calor a la portada i setmana partida en blocs:** es prefereixen respostes clares i una única graella de dilluns a divendres amb desplaçament lateral.

Nota per a qui presenta: algunes idees s'han ajornat, no rebutjat per sempre. Fonts: diari, 13:07, 13:24, 13:52, 15:32, 16:23 i «Setmana seguida fins divendres»; especificació, «5.2: què es pot moure».

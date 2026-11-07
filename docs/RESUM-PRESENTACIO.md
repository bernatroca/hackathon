# Base per a la presentació · Horaris i espais

Guió en català planer. Cada apartat proposa una diapositiva. Les fonts són documents del projecte; no s'han consultat dades reals ni fitxers de resultats per escriure aquest resum. Els camps de xifres pendents els ha de completar l'equip amb els recomptes finals.

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

Nota per a qui presenta: el pic inicial de 15 de 19 aules correspon a l'horari d'avui; no és el pic de la proposta. Font: diari, 13:24, 16:30 i 17:19. La part 1 comprova la diagnosi; les propostes de la part 2 passen pel verificador oficial.

## Part 2 · Propostes comprovades

- **5.1 · Aules:** assignar espais sense canviar dies ni hores. Veredicte oficial: **VALIDA**, sense relaxacions, amb la comprovació d'aules.
- **5.2 · Horari complet:** reorganitzar els torns, assignar aules i prioritzar la rutina. Veredicte: **VALIDA AMB RELAXACIONS DECLARADES**.
- **5.3 · Imprevistos:** reparar l'horari del 5.2 canviant el mínim. Veredicte: **VALIDA AMB RELAXACIONS DECLARADES**.
- **5.4 · Grau nou:** hi caben les 235 sessions d'un grau de 40 places sense moure cap sessió del 5.2 i amb rutina setmanal. Veredicte: **VALIDA AMB RELAXACIONS DECLARADES**.
- Totes passen el verificador oficial; la comprovació complementària de persones dona **CORRECTE** al 5.2 i als escenaris del 5.3 i el 5.4.

Nota per a qui presenta: una relaxació és una excepció declarada amb motiu, no una regla ignorada. No presentar totes les propostes com a vàlides sense excepcions. Font: diari, 18:02, 21:25 i 21:55. Aquests són els veredictes documentats, no una nova execució feta per preparar les diapositives.

## Marge d'aules · Encaixar no és suficient

- A l'hora punta del matí s'ocupen totes les aules ordinàries disponibles: 19 de 19.
- L'aulari té més aules, però se'n guarden 2 de reserva.
- Sense marge ordinari, una avaria, una reserva o un grup que creix obliga a recórrer a la reserva o a moure classes.
- Recomanem deixar **1–2 aules lliures a l'hora punta** per poder mantenir l'horari en el dia a dia.

Nota per a qui presenta: és una recomanació operativa pendent d'aconseguir, encara que la proposta passi el verificador. No sumar inventaris ni deduir un total d'aules: el recompte depèn dels espais que entren a cada comprovació. Font: diari, 19:18 i 22:00.

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

Nota per a qui presenta: no atribuir al verificador una comprovació d'aforament que no pot fer quan li falta el nombre d'alumnes. Els complements es queden fora del repositori. Font: diari, 17:40 i 22:00; especificació, «Riscos tècnics».

## Problema interessant · Torns, calendari i rutina

- La regla 1 fixa els primers cursos al matí i els cursos superiors, dobles i màsters a la tarda; l'equip no tria lliurement el torn.
- La setmana d'avaluació concentra les classes que cal moure en massa poc temps: el calendari impedeix portar-les als altres dies.
- La solució admet excepcions puntuals al torn, declarades i justificades; també declara els casos de classes fixades que necessiten aula.
- La rutina és una prioritat forta: mateix dia, hora i aula cada setmana, amb excepcions de calendari comptades i explicades.
- Quan el model complet no acabava a temps, vam passar a reparació local: primer complir les regles i després millorar.

Nota per a qui presenta: un model que no acaba no demostra que no hi hagi solució. Les excepcions per impossibilitat requereixen recompte o prova del model. Font: diari, 16:24, 18:05, 18:12, 18:23 i 21:25; especificació, «5.2: què es pot moure».

## Norma de dades · Com treballem ara

- Cap agent llegeix dades reals: treballa amb l'esquema i exemples inventats.
- El disseny i les proves visuals es verifiquen amb dades inventades.
- El codi pot comprovar les dades locals, però als agents només els arriben recomptes, errors sense valors reals i veredictes.
- Les dades i els resultats derivats queden fora del repositori; l'app és local.

Nota per a qui presenta: aquesta és la norma vigent des del vespre. Abans, segons el permís inicial comunicat a l'equip, els agents sí que havien llegit dades. El README ho explica: la neteja posterior no desfà el contingut que ja havia passat pels serveis d'IA. Font: diari, 19:09 i 20:15; [README](../README.md), «Ús de les dades del repte, abans i després de la restricció».

## Ús de la IA · Repartiment i decisions humanes

- Claude orquestra: concreta especificacions, reparteix tasques, revisa i integra els resultats.
- Subagents de Codex amb `gpt-6.1-sol` treballen per rol: dades, backend i frontend, en worktrees separats i en paral·lel.
- L'equip decideix prioritats: rutina de l'estudiant, mínims canvis, excepcions explícites i alternatives fora del lliurament principal.
- Per triar el disseny: al migdia, maquetes HTML locals (A, B, C); al vespre, quatre propostes de graella fetes amb Claude Design. L'equip tria la forma de la B amb els colors per estat de la A.
- L'equip valida l'ús real; el verificador oficial i les comprovacions de persones contrasten el que produeixen els agents.

Nota per a qui presenta: les maquetes del migdia eren HTML locals; la graella final es va triar entre quatre propostes de Claude Design (dades inventades). Font: diari, 13:17, 13:52, 17:52, 19:30 i 21:55; README, «Ús d'IA».

## Què queda per fer · Explicar els límits

- Guanyar marge d'aules a l'hora punta: la validesa actual no resol la fragilitat operativa.
- Completar la comparació final: hores mortes abans **[XIFRA]**, després **[XIFRA]**; activitats amb rutina setmanal **[XIFRA] %**.
- Revisar les excepcions amb Gestió Acadèmica i la Junta, i explicar també qualsevol indicador que empitjori.
- Tornar a verificar els fitxers finals abans del lliurament i preparar la demo i el material de reserva.
- Com a evolució: consulta personal de l'estudiant, peticions del professorat i assistent; les fonts no acrediten que aquestes ampliacions estiguin acabades.

Nota per a qui presenta: els camps pendents s'han d'omplir amb recomptes finals, sense copiar identificadors. No prometre que s'ha trobat l'horari òptim: tenim propostes validades. Fonts: especificació, «Com sabem que està fet» i «Contracte de lliurament»; diari, 15:52, 16:01 i 22:00.

## Idees descartades

- **Mesurar seients buits:** no tenim assistència real; per dimensionar, suposem que hi va tot l'alumnat matriculat.
- **Comparar pla i realitat:** falta el fitxer de l'ús real dels espais al paquet.
- **Desdoblaments per rotació i fusions al lliurament principal:** es reserven com a alternatives per a la Junta; afegeixen excepcions i el verificador no veu tota la rotació.
- **Alternatives lliures de torn:** es deixa de proposar-les per seguir la regla 1 de la Direcció.
- **Mapes de calor a la portada i setmana partida en blocs:** es prefereixen respostes clares i una única graella de dilluns a divendres amb desplaçament lateral.

Nota per a qui presenta: algunes idees s'han ajornat, no rebutjat per sempre. Fonts: diari, 13:07, 13:24, 13:52, 15:32, 16:23 i «Setmana seguida fins divendres»; especificació, «5.2: què es pot moure».

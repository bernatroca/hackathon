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

### [ds 13:17] IA · Llançats 5 subagents de Codex per a la part 1
- dades-1 (ocupació, hores-aula, aforament), dades-2 (fora de torn, hi cap el matí), dades-3 (hores mortes, dobles amb matí, marge grau nou), dades-4 (seients buits, canvis d'aula, docents a cavall) i frontend-1 (app Streamlit).
- Model gpt-6.1-sol, effort medium, sense xarxa. Cada un al seu worktree (../hack-*) i branca, només amb els seus fitxers.
- Esquelet comú (dades.py, troballes.py, comprova.py) fet per la integració abans de llançar-los, perquè no es trepitgin.

### [ds 13:24] DECISIÓ · Fora «seients buits», dins «problemes i millores»
- Pregunta de dades-4: què és una aula gran per a un grup petit?
- L'equip respon que suposem que ve tot l'alumnat matriculat. Si una aula va mig buida no ho podem saber, perquè no tenim dades d'assistència.
- La pregunta 6 passa a ser un catàleg de problemes de l'horari d'avui, cadascun amb la xifra, el càlcul i una proposta de millora.

### [ds 13:24] IA · Part 1: 4 de 5 subagents acabats a la primera
- dades-1, dades-2, dades-3 i frontend-1 han acabat en 2-4 minuts cadascun. Branques unides a main sense conflictes.
- `python -m nivell1.comprova`: 15/15 xifres de l'enunciat quadren (5.722 sense aula, pic 15 de 19, 68,25 % del matí, 2.008 fora de torn, 43 d'aforament, 248 dobles).
- DADA: amb comparació directa hi ha 3.246 sessions fora de torn; 1.238 són fixades heretades i en compten 2.008.
- DADA: cap llindar de mida d'aula falla al matí; condició necessària, no prova que hi càpiga.

### [ds 13:29] DECISIÓ · Portada de la part 1 i xifres del semestre
- Portada: Hi cap el matí (15 de 19, 68 %), Fora de torn (2.008), Sense aula (74 %), Marge per al grau nou i Problemes i millores. Responen «com s'usen» i «hi cap», i preparen el 5.4.
- La xifra gran és sempre la del semestre, perquè el jurat la pugui comparar amb l'enunciat. La setmana es veu als gràfics.
- PROBLEMA trobat en provar l'app: tema clar i fosc barrejats, textos dels gràfics il·legibles i xifres tallades a la portada. Ho arregla frontend-1 en una segona passada.

### [ds 13:52] DECISIÓ · Disseny per al coordinador: semàfor amb la resposta en gran (B1)
- PROBLEMA: la persona és un coordinador, no un informàtic. Els gràfics de l'app (mapa de calor, eixos, llegendes) no s'entenien.
- Hem fet 3 propostes en HTML (A respostes, B semàfor, C edifici) i 3 variants de la B. L'equip tria la B1:
  - a dalt, la resposta en gran («Sí, però just.») amb 19 quadrets, un per aula;
  - a sota, targetes amb color d'estat (verd, groc, vermell), la xifra, què vol dir i «Proposem:».
- Gràfics: cap mapa de calor ni gràfic tècnic a la portada. Quadrets d'aules, barres amb el número escrit i el plànol d'aules per espina (de l'opció C) al detall d'ocupació. Seguim la skill dataviz (paleta validada, colors d'estat sempre amb icona i text).
- Llibreries mirades: Plotly (ja la fem servir, bona integració), Altair i ECharts (streamlit-echarts, més vistós però menys integrat). Ens quedem amb HTML/CSS propi per a les targetes i Plotly simplificat.
- Claude Design (tipus d'artefacte) no estava disponible en aquesta sessió: les maquetes són HTML locals a docs/disseny/.

### [ds 13:52] DECISIÓ · Prompt de la part 2, esborrany v2
- Criteri que mana: un horari rutinari per a l'estudiant (mateix dia, hora i aula cada setmana; aula base per grup; poques hores mortes). Es planifica per activitat, no per sessió.
- «Fet» vol dir una xifra abans i després per a cada objectiu, calculada pel codi (`nivell2.comprova`), no la paraula del subagent.
- Titulacions comparades en percentatge, no en absolut: una gran sempre té més sessions mogudes (com qui sempre contesta les enquestes perquè té més temps).
- S'afegeixen alternatives de torn per a la Junta, imprevistos amb canvi mínim des del 5.2 i el grau nou de 40 amb la mateixa rutina.
- La graella espera el disseny confirmat del nivell 1. No es programa res fins a l'OK de l'equip. Espec: .plans/nivell2-prompt.md

### [ds 14:12] SOLUCIÓ · App de la part 1 amb el disseny B1
- frontend-1 (Codex) ha passat la B1 a Streamlit en 16 minuts. Té la resposta gran amb els 19 quadrets, targetes de semàfor amb «Proposem», 11 detalls amb un gràfic senzill i el plànol d'aules per espina.
- Textos planers a app/textos.py. El SQL queda dins «Per a tècnics».
- PROBLEMA resolt: al frontend li faltava l'inventari d'aules. L'app el llegeix amb una sola consulta, i les constants (19 aules, 2 de reserva, 40 places) porten comentari d'on surten.
- Pendent: «Com ho hem calculat» encara fa servir paraules tècniques (cohort, PLAB, llindar).

### [ds 15:32] DECISIÓ · Especificació de la part 2 afinada amb l'entrevista
- Rutina dura (mateix dia, hora i aula cada setmana; només el 5.3 trenca una setmana). Mínims canvis: un canvi d'hora pesa més que un d'aula. Qui va de tardes continua de tardes, tret que la regla 1 obligui (només al 5.2).
- Al 5.2 es pot moure qualsevol sessió movible, amb cost per canvi i preferint el mateix dia. Excepcions a la regla 1 només si es demostra que és impossible. Sense alternatives de torn; el 5.2 no deixa lloc per al grau nou.
- IDEA de l'equip: rotació de PAUL i SEM. Si un grup no cap en una aula petita, es parteix en dues meitats: la 1a hora A fa problemes de X i B de Y, i la 2a hora es canvien. Es declara R3-AFORAMENT i el nostre model reserva la 2a hora.
- IDEA de l'equip: fusionar classes repetides amb el mateix docent. Va com a proposta per a la Junta, no al 5.2 lliurat. DADA: només 2 casos reals de teoria (una assignatura de 3r amb 148 alumnes i una altra amb 108); la resta no hi cap o és fixada.
- Espec: .plans/nivell2-horari-spec.md (substitueix .plans/nivell2-prompt.md).

### [ds 15:51] DECISIÓ · Desdoblament de PAUL i SEM i punts pendents de la part 2
- Tot PAUL o SEM movible de més de 34 alumnes es parteix en dues meitats (aula petita = seminari o una aula de fins a 34 places). Amb parella, rotació: la 1a hora A fa X i B fa Y, i la 2a es canvien. Sense parella, es parteix igualment; si no hi ha hora seguida, la 2a meitat la fa un altre dia.
- DADA: 101 grups de problemes tenen de 35 a 50 alumnes i només hi ha 4 aules d'aquesta mida; avui ocupen aules de 63-90 que necessita la teoria.
- Grup de teoria que creix (5.3): aula més gran a la mateixa hora. Les excepcions a la regla 1 es demostren amb recompte o INFEASIBLE. La vista de l'estudiant posa avui i proposta costat per costat.
- Queda per confirmar el format del resum de la Junta. Espec: .plans/nivell2-horari-spec.md

### [ds 15:52] DECISIÓ · Horari oficial de diumenge: entrega a les 12:00
- Correu de l'organització: dg 12:00 lliurament de projectes; després presentacions, jurat i cloenda; s'acaba entre les 14:00 i les 15:00.
- No hi ha cap demo al jurat abans del lliurament: la demo en directe (i les 3 preguntes al nivell 3) és a la presentació.
- Pla: congelació dg 2:00; de 8:00 a 12:00 diapositives, vídeo de reserva, assajos i zip (fet cap a les 11:30).
- Dg: dutxes 9-11 al SAF, esmorzar inclòs, sense dinar. Falta saber quant dura la presentació i el format (estand o escenari).

### [ds 16:01] DECISIÓ · Per a qui és l'app, i l'escalat queda per al pitch
- Segons l'enunciat i la presentació, l'usuari és Gestió Acadèmica (el tècnic que fa i manté l'horari). La Direcció i la Junta decideixen amb el resum d'una pàgina. El docent i els estudiants només reben avisos (redactats, no enviats).
- IDEA (proper pas, no ara): obrir l'app a l'alumnat («El meu horari» amb canvis en directe) i al professorat (peticions de canvi o de classe extra validades pel verificador i aprovades per Gestió Acadèmica). Ho guardem a docs/MILLORES-PITCH.md per explicar-ho al pitch.
- Motiu de no fer-ho ara: fora de l'enunciat i de la nota, sense adreces, i docents pseudonimitzats.

### [ds 16:23] DECISIÓ · El desdoblament passa a alternativa per a la Junta
- Punt crític de la part 2: desdoblar tots els PAUL i SEM de més de 34 alumnes obligaria a declarar R3-AFORAMENT a 1.197 sessions (153 activitats). VALIDA sense relaxacions passa per davant, i el jurat no veu la meitat B.
- L'equip decideix: les propostes lliurades (5.1-5.4) van sense desdoblaments. Desdoblaments i fusions, com a alternativa per a la Junta, al final i si sobra temps.
- DADA: la tarda hi cap amb marge. La pitjor setmana demana 259 h d'aula, contra 617 h d'oferta (19 aules × 6,5 h × 5 dies). El matí, 397 h contra 570 h.

### [ds 16:24] DECISIÓ · Rutina com a prioritat forta i quatre respostes al 5.4
- La rutina (mateix dia, hora i aula cada setmana) passa de regla dura a prioritat forta. S'hi admeten excepcions puntuals per calendari o setmanes concretes, i cada una es compta i s'explica. Mai passa per davant del verificador.
- El 5.4 respon sempre una de quatre: hi cap; no hi cap sense tocar el 5.2; no l'hem trobat; hem demostrat que no existeix (recompte o INFEASIBLE d'un model complet).

### [ds 16:30] DADA · Hi cap la tarda amb 3r i 4t? Sí: el coll d'ampolla és el matí
- Dubte de l'Uri: si 3r i 4t passen a la tarda, hi haurà moltes més classes. El recompte ja les inclou.
- Pitjor setmana (2027-W09): la tarda passa de 105 h d'aula (les que avui ja hi són) a 259 h (+154 h de les 1.526 sessions de 3r i 4t que avui són al matí). Oferta: 19 aules × 6 h (15-21 h) × 5 dies = 570 h, o 617 h si comptem des de les 14.30. Ocupació: 45 %.
- Matí (pitjor setmana 2027-W06): 397 h contra 570 h, el 70 %. És el torn ajustat.
- Per mida a la tarda no falla cap llindar (p. ex. grups de més de 63 alumnes: 50 h contra 455 h).
- Per què sobra tarda: els laboratoris (PLAB) i les dobles no ocupen aules de l'aulari, i 3r, 4t i màsters tenen menys hores de teoria i problemes que 1r i 2n.

### [ds 17:09] PROBLEMA · Validació de la part 1: 22 passos bé, 5 malament
- Fallen: la resposta gran («Sí, però just», i els quadrets desborden a 768-1024 px), el 4.541 sense aula, el grau nou en verd, i «Com ho hem calculat» amb jerga.
- Millores: alçades iguals a les targetes, singulars, proporció «cap de les classes» quan és un 2 %, estat de càrrega, i % escrit al plànol.
- SOLUCIÓ en marxa: dades-1 (desglossament 4.541), dades-2 (pregunta 4 amb matí i tarda), dades-3 (grau nou corregit i provisional) i frontend-1 (textos planers, responsivitat i estats), en paral·lel.
- PROBLEMA nostre: una edició de l'integrador (abe83e1) va tallar l'especificació de la part 2; la sessió Part 2 l'ha restaurada (9c3488b).

### [ds 17:19] SOLUCIÓ · Correccions de la validació de la part 1, unides
- La resposta gran ara diu «Hi ha marge d'hores» (matí 70 %, tarda 42 %), i el més ajustat és el matí en conjunt la setmana 2027-W06. Hi ha l'estat «Pendent de validar».
- Hi ha el desglossament 5.722 = 4.541 per assignar + 919 laboratoris + 262 dobles. El grau nou queda provisional (181 h lliures a la setmana més plena, en necessita 26).
- Textos planers a «Com ho hem calculat», gràfics fixos (sense zoom ni arrossegament), alçades iguals i % escrit al plànol.
- PROBLEMA resolt: la portada quedava en blanc uns 15 s. Les hores mortes trigaven 14 s; amb SQL de finestra, 0,08 s. A més, el menú surt primer i la portada només calcula les seves 5 xifres.
- 25/25 comprovacions; tests de l'app OK. VALIDATION.md amb 17 passos marcats per reprovar.

### [ds 17:40] DADA · Alumnes reals dels 14 grups sense dada (2n semestre, 276 sessions)
- El paquet hi posa 0. Per a dues optatives de 4t hem fet servir els matriculats que publica el portal públic SIQ de la UAB. (Noms, codis i enllaços retirats d'aquest diari el ds 7-11 al vespre.)
- Les places previstes de Sigma gairebé doblaven els alumnes reals.
- Dues obligatòries de 3r, noves el 2026-27, no tenen històric: estimació amb la promoció del mateix curs al paquet.
- Una assignatura amb quatre grups de problemes ja té alumnes: és la mateixa classe que una altra (classe compartida).

### [ds 17:40] DECISIÓ · El model de la part 2 fa servir aquestes xifres
- Fitxer `dades/alumnes_sense_dada.json` (xifra, font i nota per grup). Especificació i tasca 0.3 actualitzades.
- El verificador oficial hi continua veient 0: la xifra només serveix perquè triem una aula on hi càpiguen.

### [ds 17:40] IA · Recerca de dades amb Claude
- Claude (orquestrador) va buscar al paquet, l'enunciat, l'ordinador i el Drive (no hi era). Després, al web: va trobar el SIQ i les guies docents i en va llegir les taules.

### [ds 17:47] DECISIÓ · Últims detalls de l'especificació de la part 2
- La rutina va davant dels mínims canvis. Pesos del solver: canvi de franja 10, d'aula 3, fora del passadís 2, cada 30 min d'hora morta 1.
- Les classes poden començar cada mitja hora. Si un dia nou és festiu una setmana, aquella sessió va a un altre dia de la mateixa setmana i torn, i compta com a excepció.
- B3/0021: s'hi queden les 35 sessions si no canvien de franja. Vista de l'estudiant amb selectors titulació → curs → grup. Resum de la Junta a l'app i en PDF.
- De nit, el càlcul llarg; de dia, un canvi petit triga menys d'1 minut amb reparació local (`repara`, per al 5.3 i el nivell 3).
- Les propostes de resultats/nivell2/ van a git amb una excepció del .gitignore. Quan acabi la part 2, revisarem com complim la norma de no publicar les dades.
- PROBLEMA resolt: el commit abe83e1 va tallar l'especificació de 233 a 50 línies; restaurada a 9c3488b.

### [ds 17:52] IA · Part 2: fase 0 feta i 4 subagents de Codex llançats
- Fase 0 (Claude, integració): especificació restaurada i completada, esquelet `nivell2/base.py` (el verificador hi dona les xifres de l'enunciat: 2.008, 13, 43, 54 i 4.541), excepció del .gitignore per a les propostes i worktrees antics de la part 1 tret.
- Fase 1 en paral·lel, `gpt-6.1-sol` medium, sense xarxa, un worktree per tasca (../hack-n2-*): n2-backend-1 (aules del 5.1), n2-backend-2 (franges del 5.2), n2-dades-1 (taula de xifres) i n2-frontend-1 (graella de la part 2).
- Aquesta sessió orquestra la part 2; la sessió Part 1 no hi llança subagents.

### [ds 17:57] IA · n2-dades-1 acabat i unit a main
- L'ordre `python -m nivell2.comprova <proposta>` treu la taula d'abans i després en uns 6 s; amb l'horari d'avui quadra amb l'enunciat. Té 6 proves verdes.
- PROBLEMA: faltava pytest al .venv i dos subagents van tornar BLOCKED. Ja està instal·lat. n2-frontend-1 torna a provar per un error d'imports.
- Pendent menor: quan totes les titulacions empaten a 0 %, «la que surt pitjor» les llista totes.

### [ds 17:59] IA · n2-frontend-1 acabat i unit a main
- La pàgina «Part 2 · Proposta d'horari» té selectors de proposta, setmana i grup (titulació → curs → grup), la graella de l'estudiant d'avui i de la proposta, i la vista per aula. Té 7 proves verdes i ja surt a l'app.
- Ha calgut una segona passada: amb pytest, els imports `app.components` xocaven amb app/app.py.
- Per a la fase 2: cada classe es repeteix a cada fila de 30 min. Millor un sol bloc que ocupi les seves files.

### [ds 18:02] IA · n2-backend-1: el 5.1 és VALIDA
- Assignador d'aules genèric (CP-SAT, una aula per activitat) i `python -m nivell2.s51`. El verificador oficial amb --nomes-aules diu VALIDA, sense relaxacions; triga uns 5 min. Comprovat també per la integració.
- La proposta es queda al Mac (resultats/, fora de git).
- Pendent de millora: aula base i canvis teoria-problemes fora del passadís surten pitjor que avui. Es millorarà quan hi hagi temps, amb més pes a l'aula base.

### [ds 18:05] PROBLEMA · El model de franges del 5.2 no troba solució a temps
- n2-backend-2: el model sencer (totes les sessions, tots dos torns) acaba en UNKNOWN després de 300 s. UNKNOWN no vol dir impossible.
- Com ho resolem: torna a Codex amb effort high i una estratègia de reparació local. Primer es mouen només les activitats fora de torn o de finestra; matí i tarda per separat; setmana tipus amb conflictes només entre activitats que comparteixen setmana; i primer complir, després optimitzar.

### [ds 18:12] SOLUCIÓ · El model de franges del 5.2 ja troba solució
- Amb la reparació local (moure només les activitats fora de torn, matí i tarda per separat i setmana tipus), n2-backend-2 troba solució en uns 12 s, sense sessions fora de torn ni solapaments nous de docent o alumnat. Comprovat per la integració.
- Mou només les sessions que la regla 1 obliga a moure. Les sessions que cauen en festiu es mouen a un altre dia de la mateixa setmana i surten com a excepcions.
- Fase 2 llançada: n2-backend-2 (5.2 sencer, amb aules) i n2-dades-2 (resum de la Junta). n2-frontend-2 espera que la sessió Part 1 acabi la passada de disseny d'app/.

### [ds 18:13] SOLUCIÓ · Passada de disseny de la part 1 amb les skills de disseny
- Revisió de només lectura (Codex) amb les Web Interface Guidelines de Vercel, better-ui, dataviz i la B1: 18 troballes i la paleta amb el contrast WCAG (docs/revisio-disseny-1.md).
- L'equip aprova els 10 retocs petits i els 4 canvis grans:
  - bloc gran en vermell si no hi cap;
  - semestre i setmana visibles;
  - «Veure les dades» i barres primes;
  - icones SVG, un sol h1, ?resposta=<id> i errors planers.
- Abans de canviar res: etiqueta part1-v1 per poder tornar enrere.
- Coordinació: la sessió Part 2 havia esborrat els worktrees de la part 1. S'ha refet ../hack-frontend i s'ha acordat qui toca què a app/. La part 2 continua els seus fitxers ara que la passada és a main.
- Skills noves trobades, per instal·lar a mà: jakubkrehel better-colors, better-layout i better-interface, i pbakaus impeccable.

### [ds 18:19] IA · n2-frontend-2 unit: la graella es llegeix millor
- Cada classe és un sol bloc, surt per defecte la proposta més avançada, hi ha una línia de resum per grup (canvis de franja, d'aula i de torn, i aules diferents a la setmana) i es marquen les excepcions de calendari. Té 27 proves verdes i l'he comprovat al navegador.
- Es veu a ull nu que el 5.1 fa servir massa aules diferents per grup: la millora de l'aula base passa per davant.
- Pendent de la graella: quan coincideixen subgrups, les columnes queden massa estretes.
- La pàgina de la Junta espera el format de n2-dades-2, que ha preguntat dues coses i l'equip ha respost (excepcions agrupades a la pàgina; «No s'ha explicat per què» si no hi ha motiu).

### [ds 18:23] PROBLEMA · La setmana d'avaluació d'abril no hi cap amb els torns nous
- El 5.2 complet no troba aules ni franges per a la setmana del 5 al 9 d'abril. Del dilluns al dijous és setmana d'avaluació: el verificador no hi deixa portar classes d'un altre dia, i les que han de canviar de torn s'amunteguen el divendres 9 a la tarda, on xoquen docents i grups.
- Decisió, d'acord amb l'especificació: només en aquella setmana, i només si es demostra que és impossible, es demana l'excepció a la regla 1. El mínim de sessions es queda al torn d'avui, declarades com a relaxació R1-TORN amb la prova.

### [ds 18:24] IA · n2-dades-2 unit: resum per a la Junta
- `python -m nivell2.junta <proposta>` escriu junta.json, junta.md i junta.html (una pàgina A4 per imprimir) en uns 2 s. Té 8 proves verdes, inclosa la xifra de l'enunciat del pic del matí. Els resums es queden a resultats/, fora de git.
- Llançat n2-frontend-3: la pàgina «Resum per a la Junta» a l'app. Hem avisat la sessió Part 1 que toca la navegació d'app/app.py.

### [ds 18:30] PROBLEMA · Dues xifres de la Junta confonien
- n2-frontend-3 ja ha posat la pàgina «Resum per a la Junta» a l'app (33 proves verdes, comprovada al navegador).
- En provar-la amb el 5.1 hem vist dos errors. Comptava com a canvi posar aula a una classe que no en tenia (i sortien titulacions amb el 100 % «mogudes»). I el pic comptava totes les classes, no només les aules ordinàries (deia «falten aules» amb una proposta vàlida).
- Com ho resolem: n2-dades-3 les corregeix amb el criteri del verificador (canvi d'aula només si ja en tenia, i pic d'aules ordinàries per franja d'una hora).

### Usabilitat del nivell 2 · revisió demanada per Bernat
- La consulta ha de ser entenedora per a Gestió Acadèmica: «Horari actual» són els fitxers originals i «Amb la proposta» és la millora escollida. Consultar només l'actual no dibuixa una comparació duplicada.
- S'amaguen els selectors amb un sol valor. El grup de teoria passa a dir-se «Grup d'estudiants», amb l'explicació dels subgrups; es fa explícit que es poden consultar tots els cursos i les hores de tarda.
- Les aules que falten són mancances dels fitxers originals, no classes cancel·lades. Blau sense canvis, verd aula afegida, groc classe modificada i vora discontínua cas especial: llegenda visible i text a cada classe.
- Ajuda opcional de sis passos que porta als apartats de la pàgina, amb anterior, següent i tancar. Controls compactes en mòbil. Les classes soles aprofiten l'amplada del dia; les graelles s'apilen quan no hi caben totes dues i tenen desplaçament lateral en pantalles estretes.
- Verificació funcional: 39 proves passen i 1 queda omesa en els tests de part 2, app i Junta. Comprovació al Chrome dels filtres, la consulta única i el recorregut de l'ajuda; revisada també la disposició a 390 px.

### [ds 19:09] DECISIÓ · Norma nova de la direcció: els agents ja no llegeixen dades
- Fins ara, amb el permís de l'organització, Claude i Codex treballaven amb el paquet de dades. Des d'ara, per precaució i per indicació de la direcció, cap agent llegeix dades reals: només recomptes, errors o el veredicte.
- Barreres: .claude/settings.json (Claude Code no pot llegir repte/, resultats/ ni dades/), AGENTS.md (la norma per a Codex, repetida a cada encàrrec) i .gitignore.
- L'app només s'obre des d'aquest ordinador: server.address = localhost, i el servidor de disseny lligat a 127.0.0.1.
- No separem l'app de les dades: les parts 2 i 3 en necessiten (graella i assistent). Sí que traiem de les taules que es mostren les columnes que no calen (identificadors de docent i codis).
- Pendent: treure de l'historial local el fitxer de dades i els detalls del diari abans de pujar res a GitHub (a GitHub no n'hi ha cap).

### [ds 19:18] DECISIÓ · Validació de la part 2 i tres propostes de disseny
- Validació d'en Bernat: el 5.1, la graella i la Junta funcionen; quedava una incoherència a la Junta, entre el pic (19/19 i 13/19) i la taula de mides (−3 i −6). Ja està corregida (n2-dades-4): els dos fan servir el mateix recompte d'aules ordinàries per franja.
- Millora de l'aula base unida (n2-backend-1): un grup de mostra passa de 9 aules a la setmana a 3.
- Disseny: tres propostes per a la pàgina de la part 2, amb l'estil de la part 1 i dades inventades (docs/disseny/part2-opcio-a, b i c): A, franja i pastilla; B, com era i com queda; C, colors que ressalten. Totes porten el menú agrupat i la guia a baix a l'esquerra. L'equip tria.
- La part 1 rep la petició de fer més petites les caixes de «Totes les respostes», ordenades per urgència i amb filtres.
- Pendent: la pregunta de les 458 sessions fixades sense aula del 5.2.

### [ds 19:20] DECISIÓ · Norma de dades a la part 2 i resultats de la validació
- Norma de la direcció: cap agent llegeix repte/, resultats/ ni dades/; només recomptes, errors o el veredicte. Cada encàrrec a Codex de la part 2 porta la frase de la norma. El servidor de la part 2 (8503) ja només escolta a 127.0.0.1.
- nivell2/base.py llegeix la carpeta de les dades de REPTE_DIR. Pendent per a la branca del 5.2: que franges.py imprimeixi només el nombre d'excepcions i desi el detall en un fitxer.
- Validació de l'equip, coses a arreglar de la part 2: graelles una sota l'altra en pantalla ampla (7.4), subgrups massa estrets (7.7), classe compartida que surt com dos blocs a una aula (7.9), codis de grup sense explicar (7.12) i sigles al resum de la Junta (8.7). La 8.7 ja és en marxa (n2-dades-5); la resta entra amb el disseny que triï l'equip.
- PROBLEMA: uns canvis de la pàgina de la part 2 sense commit a la carpeta principal van entrar al commit c1a5ebb d'una altra sessió, i app/components/ajuda_part2.py havia quedat fora de git. Solució: s'ha fet el commit del fitxer, i a la carpeta principal només es fan commits amb camins explícits.

### [ds 19:30] DECISIÓ · Disseny de la part 2: opció A, i tres versions de la Junta
- L'equip tria l'opció A per a l'horari proposat: franja de color i pastilla. Sense canvis en blau (no en gris), aula assignada en verd suau, canvi en taronja i cas especial en vermell, amb filtres pels mateixos colors. L'horari ha de ser el protagonista: controls compactes en una targeta i el resum en tres xifres. La guia pas a pas enfoca l'apartat i el panell surt al costat. Ho fa n2-frontend-4.
- Junta: tres versions per triar (docs/disseny/junta-opcio-a, b i c), amb colors orientatius (verd suau amb marge, taronja si va just, vermell si falten aules) i textos curts.
- A la part 1 (sessió Part 1): totes les pàgines amb l'estil de la primera, centrades; caixes més petites a la primera pàgina; filtres de «Totes les respostes» amb el color i la icona de cada estat; la capçalera que talla en fer scroll.
- Neteja de dades unida: proves amb valors inventats i el 5.1 només imprimeix recomptes (n2-neteja-1). Textos de la Junta sense sigles (n2-dades-5).

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
- IDEA de l'equip: fusionar classes repetides amb el mateix docent. Va com a proposta per a la Junta, no al 5.2 lliurat. DADA: només 2 casos reals de teoria (Assignatura Inventada A, D951, 148 alumnes; 900000, 108 alumnes); la resta no hi cap o és fixada.
- Espec: .plans/nivell2-horari-spec.md (substitueix .plans/nivell2-prompt.md).

### [ds 15:51] DECISIÓ · Desdoblament de PAUL i SEM i punts pendents de la part 2
- Tot PAUL o SEM movible de més de 34 alumnes es parteix en dues meitats (aula petita = seminari o Q9/5014). Amb parella, rotació: la 1a hora A fa X i B fa Y, i la 2a es canvien. Sense parella, es parteix igualment; si no hi ha hora seguida, la 2a meitat la fa un altre dia.
- DADA: 101 grups de problemes tenen de 35 a 50 alumnes i només hi ha 4 aules d'aquesta mida; avui ocupen aules de 63-90 que necessita la teoria.
- TE/908 (5.3): aula més gran a la mateixa hora. Les excepcions a la regla 1 es demostren amb recompte o INFEASIBLE. La vista de l'estudiant posa avui i proposta costat per costat.
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

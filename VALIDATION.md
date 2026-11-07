# La part 1 (anàlisi d'espais) i la pàgina de la part 2 (proposta d'horari) es veuen bé, s'entenen per a un coordinador i les xifres quadren amb l'enunciat

## Context

- App local: http://localhost:8501 (`.venv/bin/streamlit run app/app.py`, o la configuració «app» de `.claude/launch.json`).
- L'app no té usuaris: a tots els passos l'usuari és `cap`.
- Dades: el paquet real del repte a `repte/repte-horaris-escola/paquet/`, 2n semestre per defecte. No s'ha creat cap dada nova.
- Xifres de l'enunciat que han de sortir: 2.008 classes al torn equivocat, 5.722 sense aula (74 %), 15 de 19 aules al pic, 68 % del matí i 43 amb més alumnes que places.
- Comprovació automàtica feta: `python -m nivell1.comprova` dona 18/18 i `python app/test_app.py` dona OK.
- Part 2: la proposta 5.1 és a `resultats/nivell2/5.1/` (només al Mac, fora de git). Comprovació automàtica feta: el verificador oficial amb `--nomes-aules` diu VALIDA; `python -m nivell2.comprova <proposta>` treu la taula d'abans i després; `pytest app/test_part2.py` (7), `nivell2/test_xifres.py` (6) i `nivell2/test_aules.py` (8) passen. El 5.2 encara no hi és. Si l'app del port 8501 ja estava oberta abans, s'ha de reiniciar per veure la part 2 nova (o fer servir http://localhost:8503, configuració «app-part2»).

## Portada «Com estem avui»

1. [cap @ /] Obre l'app → surt «Com estem avui» amb fons clar, menú a l'esquerra i cap error vermell.
2. [cap @ /] Mira el bloc gran de dalt → hi ha la pregunta «Si 1r i 2n fan classe al matí, hi cabem?», la resposta en gran i 19 quadrets (15 ocupats, 4 lliures i 2 amb vora discontínua).
3. [cap @ /] Llegeix la resposta gran → no diu «Sí» a seques: parla de marge d'hores i diu que l'horari el valida la part 2 (si encara diu «Sí, però just», anota-ho: és una correcció pendent).
4. [cap @ /] Mira les targetes de sota → n'hi ha 4, cada una amb etiqueta de color amb icona i text (Cal actuar, Vigilar o Hi cap), una xifra gran, una frase i «Proposem:».
5. [cap @ /] Busca la targeta «Classes al torn equivocat» → la xifra és 2.008 i la frase diu que és 1 de cada 4 classes.
6. [cap @ /] Busca la targeta «Classes sense aula» → la xifra és 74 % (5.722) i diu quantes cal assignar de debò (4.541); si no ho diu, anota-ho com a pendent.
7. [cap @ /] Busca la targeta del grau nou de 40 places → diu si les hores són d'una setmana o del semestre, i no surt en verd fins que la part 2 ho validi; si no és així, anota-ho.
8. [cap @ /] Llegeix totes les targetes com si fossis el coordinador → no hi surten paraules tècniques com «R1-TORN», «heretades», «cohort», «bloc» o «llindar».

## Detall «Hi cap el matí?»

1. [cap @ /] Clica «Com ho sabem →» del bloc gran → s'obre el detall amb la pregunta, la resposta i els 19 quadrets.
2. [cap @ /] Mira el gràfic de barres → hi ha 5 barres (dilluns a divendres) amb el número escrit a sobre (14, 15, 11, 13, 12) i una línia discontínua vermella a 19.
3. [cap @ /] Baixa fins a «Què vol dir», «Proposem» i «Com ho hem calculat» → els tres apartats hi són i es llegeixen sense saber programar.
4. [cap @ /] Obre el desplegable «Per a tècnics: consulta SQL i sessions d'exemple» → surt la consulta SQL i uns quants `id_sessio`.
5. [cap @ /] Copia un `id_sessio` d'exemple i busca'l a `paquet/sessions.csv` → la sessió existeix i és de 1r o 2n.
6. [cap @ /] Clica «← Torna a les respostes» → tornes a la portada.

## Detall de les altres targetes de la portada

1. [cap @ /] Clica «Com ho sabem →» de «Classes al torn equivocat» → s'obre amb un gràfic de barres horitzontals amb el valor escrit, sense mapa de calor ni llegenda innecessària.
2. [cap @ /] Torna i clica «Com ho sabem →» de «Classes sense aula» → s'obre amb un gràfic senzill i la mateixa xifra que la targeta.
3. [cap @ /] Torna i clica «Com ho sabem →» del grau nou → s'obre i explica quantes hores d'aula necessita contra les que queden lliures.
4. [cap @ /] Torna i clica «Veure'ls →» o «Com ho sabem →» de «Altres problemes de l'horari» → surt una llista de problemes, cadascun amb xifra i proposta.

## Totes les respostes

1. [cap @ /respostes] Obre «Totes les respostes» al menú → surten les 11 respostes en targetes petites, amb «Es mostren 11 de 11» a dalt. (reprova)
2. [cap @ /respostes] Mira com es reparteixen → 3 columnes en pantalla ampla, 2 en pantalla mitjana i 1 al mòbil. (reprova)
3. [cap @ /respostes] Mira l'ordre → primer les «Cal actuar» (vermelles), després «Vigilar» i «Pendent de validar» (grogues) i al final les «Hi cap» (verdes).
4. [cap @ /respostes] A «Estat», desmarca «Vigilar» → només queden les vermelles i les verdes, i el recompte baixa.
5. [cap @ /respostes] Torna a marcar «Vigilar» i a «Respostes» tria «Un grau nou de 40 places» → només surt aquesta targeta i diu «Es mostren 1 de 11».
6. [cap @ /respostes] Desmarca els tres estats → surt «Cap resposta coincideix amb els filtres» amb què cal canviar.
7. [cap @ /respostes] Llegeix la targeta del grau nou → diu 26 h a la setmana, 181 h lliures i 4.679 h de marge en tot el semestre.
8. [cap @ /respostes] Prem «Com ho sabem →» d'una targeta → s'obre el detall; a «Detalls informàtics» surt la consulta SQL i cap identificador de sessió.
9. [cap @ /respostes] Obre «Com fem servir les aules?» → surt el plànol de les 21 aules per espina (Q1 a Q4) i planta, més fosques com més ocupades.
10. [cap @ /respostes] Passa el ratolí per sobre d'una aula del plànol → surt el codi, les places i el % d'ocupació.
11. [cap @ /respostes] Llegeix la nota sota el plànol → explica que moltes aules semblen buides perquè 3 de cada 4 classes no tenen aula a les dades.

## Opcions i menú

1. [cap @ /] Obre el desplegable «Opcions» del menú → hi ha el selector de semestre (2n per defecte) i de setmana.
2. [cap @ /] Canvia el semestre a 1r → la portada es torna a calcular sense error i les xifres canvien.
3. [cap @ /] Torna a posar el 2n semestre → tornen a sortir 2.008 i 74 %.
4. [cap @ /] Mira el menú → hi ha «Part 2 · Proposta d'horari» sense «aviat», i «Imprevistos» i «Pregunta-ho» surten marcats com «aviat».

## Canvis visuals

1. [cap @ /] Mira la pàgina sencera → fons clar, menú blanc a l'esquerra i cap barra fosca de Streamlit; colors i tipografia com a la maqueta B1.
2. [cap @ /] Mira sota el títol «Com estem avui» → hi ha una franja visible amb el semestre i la setmana que es mostren (p. ex. «2n semestre · setmana típica 2027-W05»).
3. [cap @ /] Mira l'etiqueta d'estat del bloc gran → és un cercle amb icona (✓, ! o ✕) i text al costat, igual que a la maqueta B1, no un caràcter solt.
4. [cap @ /] Llegeix el bloc gran → diu «Hi ha marge d'hores» amb el matí i la tarda en % enters, i «el més ajustat: el matí en conjunt» (no «aules de més de 0 places»).
5. [cap @ /] Mira els quadrets → 15 ocupats, 4 lliures i 2 de reserva amb vora discontínua, i la llegenda no parteix cap paraula.
6. [cap @ /] Fes la finestra de 1024 px d'ample amb el menú obert → el bloc gran no desborda ni talla els quadrets per la dreta.
7. [cap @ /] Mira les 4 targetes → les de cada fila fan la mateixa alçada i «Proposem» i «Com ho sabem →» queden a la mateixa línia.
8. [cap @ /] Mira els enllaços «Com ho sabem →» → són d'un blau fosc que es llegeix bé sobre blanc.
9. [cap @ /?resposta=fora-torn] Obre aquesta adreça → s'obre directament el detall «Classes al torn equivocat».
10. [cap @ /?resposta=fora-torn] Intenta fer zoom amb la roda o arrossegar el gràfic → no es mou ni s'amplia; en passar el ratolí per sobre d'una barra surt el valor.
11. [cap @ /?resposta=fora-torn] Mira les barres → són primes (no blocs gruixuts) i cada una porta el número escrit al final.
12. [cap @ /?resposta=fora-torn] Obre «Veure les dades» sota el gràfic → surt una taula amb noms de columna planers i números alineats a la dreta.
13. [cap @ /?resposta=fora-torn] Llegeix «Com ho hem calculat» → frases planeres sense «cohort», «PLAB» ni «llindar»; el SQL és dins «Detalls informàtics».
14. [cap @ /?resposta=fora-torn] Clica «← Torna a les respostes» → tornes a la portada i l'adreça perd el `?resposta=`.
15. [cap @ /?resposta=hi-cap-mati] Mira el gràfic → 5 barres (dilluns a divendres) amb el número a sobre i una línia discontínua vermella a 19.
16. [cap @ /respostes] Mira la graella → 2 columnes, targetes de la mateixa alçada i botons alineats.
17. [cap @ /respostes] Obre «Com fem servir les aules?» → el plànol té el % escrit dins de cada aula i el text es llegeix bé tant a les clares com a les fosques.
18. [cap @ /respostes] Prem Tab fins arribar a una aula del plànol → l'aula queda marcada amb un contorn blau.
19. [cap @ /] Canvia el semestre a «Opcions» → mentre calcula, el contingut es veu atenuat (no desapareix) i surt «Calculant…».
20. [cap @ /] Fes la finestra de mòbil (390 px) → una sola columna, sense espais buits grans sota «Proposem».
21. [cap @ /] Obre l'app en una pantalla ampla (més de 1.600 px) → el contingut queda centrat, amb el mateix marge a cada costat.
22. [cap @ /respostes] Canvia a «Totes les respostes» en la mateixa pantalla ampla → també queda centrada, com la portada.
23. [cap @ /] Mira les quatre caixes de sota la resposta gran → són més baixes que abans, amb la xifra i els textos una mica més petits.
24. [cap @ /respostes] Mira el filtre «Estat» → «Cal actuar» en vermell amb la creu, «Vigilar» en groc amb el signe d'admiració i «Hi cap» en verd amb el check, com les etiquetes de les targetes.
25. [cap @ /respostes] Desmarca «Vigilar» → la pastilla queda blanca amb la icona grisa, i torna a tenir color en marcar-la.
26. [cap @ /respostes] Mira una etiqueta verda «Hi cap» → el verd és més apagat que abans i es llegeix bé.

## Part 2 · Proposta d'horari

1. [cap @ /part2] Obre «Part 2 · Proposta d'horari» al menú → surt la pàgina amb «Com funciona? Guia pas a pas», «Tria què vols veure», «Setmana que vols consultar» i cap error vermell. (reprova)
2. [cap @ /part2] Mira la millora disponible → la 5.1 diu «Assignar aules, sense canviar dies ni hores». Si només n'hi ha una, es mostra com a dada, sense selector; si n'hi ha més, es poden triar amb noms entenedors. (reprova)
3. [cap @ /part2] Tria «Només l'horari actual» → es mostra una única graella dels estudiants, titulada «Horari actual · dades originals», sense comparació duplicada. Torna a «Comparar horari actual i proposta». (reprova)
4. [cap @ /part2] A «Tria els estudiants» tria Gestió de Ciutats Intel·ligents i curs 1r → s'explica que el grup és el 61 i no hi ha selector si és l'únic. Les graelles diuen «Horari actual · dades originals» i «Amb la proposta»; van costat per costat si hi ha prou espai i s'apilen en pantalles petites. (reprova)
5. [cap @ /part2] Mira la proposta 5.1 amb el mateix grup → s'explica que l'aula falta als fitxers originals, no que les classes no es facin. Les classes «Aula no indicada a les dades» tenen aula a la proposta, són verdes i no canvien de dia ni d'hora. (reprova)
6. [cap @ /part2] Llegeix «Què canvia amb la proposta?» → diferencia les aules afegides dels canvis de dia/hora/aula existent. «Detall dels canvis» mostra els recomptes; afegir una aula no compta com moure una classe. (reprova)
7. [cap @ /part2] Mira una classe de 2 hores a la graella → és un sol bloc que ocupa 4 files de 30 minuts, amb l'assignatura, el tipus en paraules, les hores i l'aula; anota si el text queda massa estret quan coincideixen subgrups. (reprova)
8. [cap @ /part2] Amb la proposta 5.1 i el grup 61, llegeix quantes aules diferents fa servir el grup → ara en són 3 (abans 9), amb la teoria sempre a la mateixa aula i els problemes al mateix passadís. (reprova)
9. [cap @ /part2] Baixa a «Consulta una aula» i tria una aula qualsevol de la llista → surt la seva graella setmanal. Si coincideixen assignatures, comprova si són una classe compartida o un solapament real. (reprova)
10. [cap @ /part2] Clica «Descarrega l'horari d'aquesta aula» → es baixa un HTML autònom amb la mateixa graella i la llegenda. (reprova)
11. [cap @ /part2] Canvia «Setmana que vols consultar» a la setmana del 15 de març → les graelles es tornen a dibuixar sense error. (reprova)
12. [cap @ /part2] Llegeix les classes → el tipus s'escriu en paraules i els grups diuen «Grup» o «Subgrup», sense TE/PAUL/SEM. (reprova)
13. [cap @ /part2] Canvia de curs → també es poden consultar els cursos superiors i les classes de tarda; es mostra tot el dia, de 8.30 a 21.00. (reprova)
14. [cap @ /part2] Llegeix la llegenda → blau sense canvis, verd aula afegida, groc classe modificada i vora discontínua cas especial; el significat també està escrit i no depèn només del color. (reprova)
15. [cap @ /part2] Obre «Com funciona? Guia pas a pas» → recorre els sis passos amb «Següent» i «Anterior», enfoca l'apartat que explica i es pot tancar o acabar; comprova-ho també en una pantalla estreta. (reprova)

## Resum per a la Junta

1. [cap @ /junta] Obre «Resum per a la Junta» al menú, just sota «Part 2 · Proposta d'horari» → surt la pàgina amb el selector de proposta i cap error vermell.
2. [cap @ /junta] Mira el selector sense tocar-lo → hi ha la «5.1» triada i l'avís «El resum definitiu sortirà amb la proposta del 5.2».
3. [cap @ /junta] Llegeix «Pic de classes alhora» i la taula «Aules que falten o sobren per mida» amb la 5.1 → el matí diu 19/19 i la tarda 13/19, i la taula de mides suma el mateix, sense cap mida en negatiu (ja no surt −3 ni −6, ni 22/19 o 25/19 a l'HTML). (reprova)
4. [cap @ /junta] Llegeix «Sessions mogudes per titulació i curs» amb la 5.1 → totes surten a 0 % de canvis de dia o d'hora, perquè la 5.1 no mou cap hora.
5. [cap @ /junta] Mira com s'ordenen les titulacions → en percentatge de les seves sessions, amb el nombre al costat, mai només amb el nombre.
6. [cap @ /junta] Clica el botó de descarregar el resum → es baixa un HTML; obre'l amb doble clic des de Baixades i imprimeix-lo en PDF: ha de cabre en un sol A4. (reprova)
7. [cap @ /junta] Llegeix tota la pàgina com si fossis de la Junta → no hi surten sigles tècniques sense explicar.

## Disseny de la part 2 · tria A, B o C

1. [cap @ http://127.0.0.1:8600/part2-opcio-a.html] Obre l'opció A (cal la configuració «disseny» engegada) → les classes porten una franja de color a l'esquerra i una pastilla «Aula assignada», «Canvia» o «Cas especial»; els botons de sobre la graella filtren.
2. [cap @ http://127.0.0.1:8600/part2-opcio-b.html] Obre l'opció B → una sola graella: les classes que no canvien són grises i les que canvien diuen ratllat com eren i, a sota, com queden; la casella «Mostra només les que canvien» amaga les grises.
3. [cap @ http://127.0.0.1:8600/part2-opcio-c.html] Obre l'opció C → cada classe té un fons de color (blau, verd, groc, ratllat vermell) amb una icona; clicar un color de la llegenda deixa només aquelles classes ressaltades.
4. [cap @ http://127.0.0.1:8600/part2-opcio-a.html] Mira la barra de l'esquerra a qualsevol opció → menú agrupat en «Com està l'horari», «La proposta» i «Ajuda», amb «aviat» en petit al costat del que encara no hi és.
5. [cap @ http://127.0.0.1:8600/part2-opcio-a.html] Clica «Guia pas a pas» a baix a l'esquerra → s'obre un panell fosc de 4 passos que ressalta cada apartat; la dreta queda lliure per a l'assistent de la part 3.
6. [cap @ http://127.0.0.1:8600/part2-opcio-b.html] Compara les tres opcions → digues quina t'agrada més (o què agafaries de cadascuna) per passar-la a l'app.

## Resum per a la Junta · tria A, B o C

1. [cap @ http://127.0.0.1:8600/junta-opcio-a.html] Obre la versió A (cal la configuració «disseny» engegada) → dos semàfors grans, matí i tarda, amb quadrets: el matí 19 de 19 surt taronja («Hi cap, just») i la tarda 13 de 19, verd suau; a sota, barres per curs i una línia d'excepcions.
2. [cap @ http://127.0.0.1:8600/junta-opcio-b.html] Obre la versió B → quatre preguntes amb la resposta en una frase gran i una pastilla de color; cap taula.
3. [cap @ http://127.0.0.1:8600/junta-opcio-c.html] Obre la versió C → quatre fitxes petites a dalt, i a sota les barres per curs i una taula curta d'aules per mida.
4. [cap @ http://127.0.0.1:8600/junta-opcio-a.html] Mira els colors a les tres versions → verd suau només si sobra marge, taronja si va just i vermell si calen més aules de les que hi ha; el verd no destaca massa.
5. [cap @ http://127.0.0.1:8600/junta-opcio-b.html] Compara-les → digues quina vols a l'app (les xifres són inventades, només per triar el disseny).

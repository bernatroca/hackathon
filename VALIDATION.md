# La part 1 (anàlisi d'espais) i la pàgina de la part 2 (proposta d'horari) es veuen bé, s'entenen per a un coordinador i les xifres quadren amb l'enunciat

## Context

- App local: http://localhost:8501 (`.venv/bin/streamlit run app/app.py`, o la configuració «app» de `.claude/launch.json`).
- L'app no té usuaris: a tots els passos l'usuari és `cap`.
- Dades: el paquet real del repte a `repte/repte-horaris-escola/paquet/`, 2n semestre per defecte. No s'ha creat cap dada nova.
- Xifres de l'enunciat que han de sortir: 2.008 classes al torn equivocat, 5.722 sense aula (74 %), 15 de 19 aules al pic, 68 % del matí i 43 amb més alumnes que places.
- Comprovació automàtica feta: `python -m nivell1.comprova` dona 18/18 i `python app/test_app.py` dona OK.
- Part 2: la proposta 5.1 és a `resultats/nivell2/5.1/`. Comprovació automàtica feta: el verificador oficial amb `--nomes-aules` diu VALIDA; `python -m nivell2.comprova <proposta>` treu la taula d'abans i després; `.venv/bin/python -m pytest -q nivell2 app` dona 107 correctes i 2 omeses. El 5.2 encara no hi és. Si l'app del port 8501 ja estava oberta abans, s'ha de reiniciar per veure la part 2 nova (o fer servir http://localhost:8503, configuració «app-part2»).

## Portada «Com estem avui»

1. [cap @ /] Obre l'app → surt «Com estem avui» amb fons clar, menú a l'esquerra i cap error vermell.
2. [cap @ /] Mira el bloc gran de dalt → hi ha la pregunta «Si 1r i 2n fan classe al matí, hi cabem?», la resposta en gran i 19 quadrets (15 ocupats, 4 lliures i 2 amb vora discontínua).
3. [cap @ /] Llegeix la resposta gran → no diu «Sí» a seques: parla de marge d'hores i diu que l'horari el valida la part 2 (si encara diu «Sí, però just», anota-ho: és una correcció pendent).
4. [cap @ /] Mira les targetes de sota → n'hi ha 4, cada una amb un títol curt, una xifra gran, una sola frase curta, l'etiqueta d'estat i «Com ho sabem →»; cap text surt de la caixa ni es talla per dalt o per baix.
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

1. [cap @ /respostes] Obre «Totes les respostes» al menú → surten les 11 respostes en targetes petites, amb «Es mostren 11 de 11» a dalt.
2. [cap @ /respostes] Mira com es reparteixen → 3 columnes en pantalla ampla, 2 en pantalla mitjana i 1 al mòbil.
3. [cap @ /respostes] Mira l'ordre → primer les «Cal actuar» (vermelles), després «Vigilar» i «Pendent de validar» (grogues) i al final les «Hi cap» (verdes).
4. [cap @ /respostes] A «Estat», desmarca «Vigilar» → només queden les vermelles i les verdes, i el recompte baixa.
5. [cap @ /respostes] Torna a marcar «Vigilar» i a «Respostes» tria «Un grau nou de 40 places» → només surt aquesta targeta i diu «Es mostren 1 de 11».
6. [cap @ /respostes] Desmarca els tres estats → surt «Cap resposta coincideix amb els filtres» amb què cal canviar.
7. [cap @ /respostes] Llegeix la targeta del grau nou → diu 26 h a la setmana, 181 h lliures i 4.679 h de marge en tot el semestre. (reprova)
8. [cap @ /respostes] Prem «Com ho sabem →» d'una targeta → s'obre el detall; a «Detalls informàtics» surt la consulta SQL i cap identificador de sessió.
9. [cap @ /respostes] Obre «Com fem servir les aules?» → surt el plànol de les 21 aules per espina (Q1 a Q4) i planta, més fosques com més ocupades.
10. [cap @ /respostes] Passa el ratolí per sobre d'una aula del plànol → surt el codi, les places i el % d'ocupació.
11. [cap @ /respostes] Llegeix la nota sota el plànol → explica que moltes aules semblen buides perquè 3 de cada 4 classes no tenen aula a les dades.

## Opcions i menú

1. [cap @ /] Obre el desplegable «Opcions» del menú → hi ha el selector de semestre (2n per defecte) i de setmana.
2. [cap @ /] Canvia el semestre a 1r → la portada es torna a calcular sense error i les xifres canvien.
3. [cap @ /] Torna a posar el 2n semestre → tornen a sortir 2.008 i 74 %.
4. [cap @ /] Mira el menú → està agrupat en «Com està l'horari» i «La proposta», amb «Horari proposat», «Resum per a la Junta» i «Imprevistos» sense «aviat»; no hi ha secció «Ajuda»: l'assistent és el botó «Assistent» de baix a la dreta. (reprova)

## Canvis visuals

1. [cap @ /] Mira la pàgina sencera → fons clar, menú blanc a l'esquerra i cap barra fosca de Streamlit; colors i tipografia com a la maqueta B1.
2. [cap @ /] Mira sota el títol «Com estem avui» → hi ha una franja visible amb el semestre i la setmana que es mostren (p. ex. «2n semestre · setmana típica 2027-W05»).
3. [cap @ /] Mira l'etiqueta d'estat del bloc gran → és un cercle amb icona (✓, ! o ✕) i text al costat, igual que a la maqueta B1, no un caràcter solt.
4. [cap @ /] Llegeix el bloc gran → hi ha la pregunta, «Sí, hi cap» amb l'etiqueta verda, una sola frase curta i els quadrets d'aules al costat; el text no surt del rectangle i té el mateix marge per tots quatre costats. (reprova)
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
26. [cap @ /respostes] Mira la pastilla «Hi cap» del filtre → el verd és més apagat que abans i es llegeix bé.
27. [cap @ /] Obre la portada en un portàtil (1.440 × 900) amb el menú obert → es veu tot sense fer scroll: el títol, la resposta gran i les quatre caixes en una fila.
28. [cap @ /] Plega el menú amb ««» → la portada continua cabent a la pantalla.
29. [cap @ /] Amb el menú plegat, mira a dalt a l'esquerra → hi ha un botó blanc amb «»» ben visible, que no tapa el títol, i en prémer-lo s'obre el menú.
30. [cap @ /] Mira el menú lateral → els noms de les seccions («Com està l'horari», «La proposta», «Ajuda») surten en majúscules i negreta, diferents de les pàgines.
31. [cap @ /] Mira les pàgines del menú → cadascuna té una icona al davant.
32. [cap @ /] Fes la finestra de mòbil (375 px) i plega el menú → el botó d'obrir-lo no tapa «Com estem avui».
33. [cap @ /] Fes scroll a la portada → cap barra talla la part de dalt del contingut.
34. [cap @ /] Mira els «Com ho sabem →» del bloc gran i de les caixes → són enllaços blaus iguals, amb el text sencer (no es talla ni per dalt ni per baix).
35. [cap @ /] Mira el bloc «Si 1r i 2n fan classe al matí, hi cabem?» → els quadrets de les aules són al costat de la resposta, centrats i ben visibles, no arraconats a la dreta.
36. [cap @ /] Mira el mateix bloc → poc marge a dalt i a baix; la línia petita del final queda just sota el text.
37. [cap @ /] Mira la vora esquerra del bloc gran → és verda, com l'etiqueta «Hi cap».
38. [cap @ /] Llegeix la línia petita del final del bloc gran → acaba amb «Validat amb l'horari proposat de la part 2 (verificador oficial)».
39. [cap @ /] Mira la caixa «Un grau nou de 40 places» → etiqueta verda «Hi cap» i una frase que diu quantes de les 235 sessions noves surten de la seva hora (41) i que no es mou cap classe de l'horari proposat; no diu «sense moure cap classe». (reprova)
40. [cap @ /] Llegeix el «Proposem» de la mateixa caixa → «Incorporar-lo a l'horari proposat: ja hi cap». (reprova)
41. [cap @ /respostes] Mira l'ordre de «Totes les respostes» → «Un grau nou de 40 places» i «Si 1r i 2n fan classe al matí, hi cabem?» surten al final, amb les verdes.

## Part 2 · Horari proposat

1. [cap @ /part2] Obre «Horari proposat» al menú (grup «La proposta») → surt el títol, una caixa amb «Què vols veure», «Proposta», «Setmana», «Estudis», «Curs» i «Grup», i cap error vermell.
2. [cap @ /part2] Mira «Proposta» i «Grup» → la proposta és «Aules assignades (5.1)»; si el curs només té un grup, «Grup» surt desactivat amb el seu nom i no queda tapat ni encavalcat amb «Curs».
3. [cap @ /part2] A «Estudis» tria Gestió de Ciutats Intel·ligents i Sostenibles i a «Curs» 1r → el resum diu «Es conserva el dia i l'hora», que la proposta assigna aula a 15 classes que no en tenien, 0 canvis d'hora, 0 canvis d'aula i 4 aules a la setmana. Els tres números queden centrats damunt de les seves etiquetes, en tres columnes iguals, també al mòbil. (reprova)
4. [cap @ /part2] Mira «La setmana del grup» en una pantalla de 1280 px → hi ha una sola graella seguida amb Dilluns, Dimarts, Dimecres, Dijous i Divendres, en aquest ordre; no es parteix en taules separades per dies. Hi cap sencera fins al divendres sense desplaçar-se de costat, i els cinc dies tenen la mateixa amplada encara que un dia tingui més subgrups.
5. [cap @ /part2] Mira el dilluns a les 10.30 → les classes que coincideixen van en carrils costat per costat; els dies i les hores sense coincidències ocupen tota la columna.
6. [cap @ /part2] Mira les classes → són rectangles arrodonits sense franja ni icones; el fons diu l'estat (blau sense canvis, verd aula assignada, taronja canvia, vermell cas especial), igual que la llegenda de dalt; les que canvien porten una línia curta com «Abans: dijous 12:30». (reprova)
7. [cap @ /part2] Clica la pastilla «Aula assignada (15)» de sobre la graella → aquestes classes queden ressaltades i la resta s'atenua; amb «Sense canvis (0)» totes queden atenuades i «Totes» ho torna a deixar com abans.
8. [cap @ /part2] A «Què vols veure» tria «Només avui» → surt l'horari d'avui sense pastilles de canvi; torna a «Proposta i avui».
9. [cap @ /part2] Mira una classe de 2 hores → és un sol bloc amb l'assignatura, les hores, «Grup» o «Subgrup» en paraules, el tipus (teoria, problemes, seminari) i l'aula; sense TE, PAUL ni SEM.
10. [cap @ /part2] Amb el grup 61, compta les aules diferents → en són 3 (abans 9), amb la teoria sempre a la mateixa aula.
11. [cap @ /part2] Canvia «Setmana» a la setmana del 15 de març → la graella es torna a dibuixar sense error.
12. [cap @ /part2] Canvia a un curs superior → surten les classes de tarda i el dia sencer, de 8.30 a 21.00. (reprova)
13. [cap @ /part2] Baixa a la consulta per aula, tria'n una i clica descarregar → es baixa un HTML autònom amb la mateixa graella i la llegenda.
14. [cap @ /part2] Mira a baix a l'esquerra → hi ha «Com funciona? Guia pas a pas», per sobre de la barra lateral; la dreta de la pàgina queda lliure.
15. [cap @ /part2] Clica la guia → «Pas 1 de 6» ressalta «Què vols veure» amb un contorn blau, la resta queda enfosquida i el panell surt al costat de l'apartat.
16. [cap @ /part2] Clica «Següent» fins al pas 6 i després «Anterior» → a cada pas el panell es mou al costat de l'apartat que explica i la pàgina s'hi desplaça sola.
17. [cap @ /part2] Prem Esc amb la guia oberta → la guia es tanca i l'enfosquiment desapareix; «Tanca» fa el mateix.
18. [cap @ /part2] Fes la finestra de mòbil (390 px) i obre la guia → el panell es veu sencer i no tapa l'apartat ressaltat.
19. [cap @ /part2] Fes la finestra de mòbil (390 px) i desplaça lateralment la graella → arribes a Divendres dins de la mateixa taula, amb la columna d’hores sempre visible i els subgrups simultanis costat per costat.
20. [cap @ /part2] Tria un curs amb subgrups simultanis i classes curtes i mira cada casella → cap text surt per sota de la casella ni trepitja la classe de sota; el nom llarg s'acaba amb «…».
21. [cap @ /part2] Mira la classe més curta de la setmana (al 2n semestre no n'hi ha de 30 minuts; les més curtes són d'1 h) → hi cap el nom (escurçat si cal), l'hora i, si canvia, la línia «Abans»; tipus, grup i nota s'amaguen abans que el nom. (reprova)
22. [cap @ /part2] Passa el ratolí per sobre d'una classe estreta amb el nom escurçat i després clica-la → el nom sencer surt a l'etiqueta flotant i el detall s'obre en un requadre ample per sobre de la graella, sense estirar el bloc; es tanca clicant fora o amb Esc. (reprova)
23. [cap @ /part2] Tria GEET (Enginyeria Electrònica de Telecomunicació), 1r, grup 31, setmana típica, i mira el dijous → els subgrups simultanis (dos) van estrets costat per costat, els noms s'escurcen amb «…» sense partir paraules, i el selector de grup diu «Grup 31», el mateix que la graella. (reprova)
24. [cap @ /part2] Tria Enginyeria Informàtica, 3r, i mira una classe d'un doble grau → diu «Amb el grup … · Aula …» o «Classe compartida amb un altre grup», mai «Pendent d’assignar aula».

## Resum per a la Junta

1. [cap @ /junta] Obre «Resum per a la Junta» al menú → surt per defecte «Horari complet (5.2)», sense l'avís antic del 5.2, i cap error vermell.
2. [cap @ /junta] Mira les fitxes de matí i tarda → «X de 19 aules» amb la frase «L'aulari té 21 aules ordinàries; en guardem 2 de reserva per a imprevistos.»; si és 19 de 19, etiqueta taronja «Sense marge» i «Si una aula falla, cal fer servir la reserva.».
3. [cap @ /junta] Tria «Aules assignades (5.1)» i mira «Curs més afectat» → diu «Cap» i «Cap curs canvia de dia ni d'hora.», perquè la 5.1 no mou cap hora; els canvis d'aula surten a part, en un indicador propi. (reprova)
4. [cap @ /junta] Tria «Aules assignades (5.1)» i mira «Excepcions noves als torns» → 0 classes amb pastilla verda «Cap», i a sota quantes classes ja es fan avui fora del seu torn i no es toquen.
5. [cap @ /junta] Amb «Horari complet (5.2)», mira «Excepcions noves als torns» → 459 classes, i a sota l'apartat «Excepcions als torns» amb cada motiu, quantes classes i quines titulacions; el cas S04526 surt destacat.
6. [cap @ /junta] Llegeix sota les fitxes → «màxim de classes alhora» del matí i de la tarda (tarda 17 a les 15:00), separat de les aules ocupades a l'hora punta (18 a la tarda), amb una frase que explica per què difereixen (un laboratori en aula ordinària ocupa aula però no compta com a classe). (reprova)
7. [cap @ /junta] Tria «Aules assignades (5.1)» i mira «Classes que canvien d'horari o d'aula, per curs» → compta també els canvis d'aula, no només els de dia o hora.
8. [cap @ /junta] Mira la taula «Aules per mida a l'hora més plena» amb «Matí» → «Hi cap» on queden aules lliures (0 de 1, 6 de 7), «Just» on estan totes ocupades (4 de 4) i «Falten» només si n'hi ha més que aules.
9. [cap @ /junta] Tria «Tarda» a sobre de la taula → la taula canvia a les xifres de la tarda.
10. [cap @ /junta] Clica «Descarrega el resum A4» → es baixa un HTML; obre'l amb doble clic des de Baixades i imprimeix-lo en PDF: cap en un sol A4 i separa les excepcions noves de les d'avui. (reprova)
11. [cap @ /junta] Llegeix tota la pàgina com si fossis de la Junta → frases curtes i planeres, sense sigles tècniques; el detall tècnic queda tancat dins «Detall tècnic».
12. [cap @ /junta] Obre «Detall tècnic» → hi ha el paràgraf «Per què 19 de 19 no és prou», en paraules planeres, i també surt a l'A4 descarregat.
13. [cap @ /junta] Obre la Junta en dues pestanyes alhora i canvia de proposta a totes dues → cap mostra l'error genèric; si el resum s'ha de tornar a calcular, surt al cap d'uns segons amb les xifres de la proposta actual.
14. [cap @ /junta] Amb «Horari complet (5.2)» llegeix les excepcions → «1 classe» (no «1 classes»), «sense curs a les dades» (no «curs desconegut») i el cas de la setmana d'avaluació en paraules planeres, sense «diagnostic.md». — també dins «Detall tècnic». (reprova)

## Imprevistos

1. [cap @ /imprevistos] Obre «Imprevistos» al menú → surt el títol, «Partim de l’horari proposat i recol·loquem les classes afectades» amb quantes classes més es mouen per fer lloc, i cap error vermell.
2. [cap @ /imprevistos] Mira el resum de dalt → «Comprovat amb el verificador oficial», quantes classes canvien d'aula, quantes de dia o hora, en quants segons, i una frase que explica per què el verificador compta una classe menys d'aula (la cancel·lada).
3. [cap @ /imprevistos] A «Què canvia», tria «Altres classes mogudes» → surten les classes que es mouen per fer lloc, amb abans i després. (reprova)
4. [cap @ /imprevistos] Mira les quatre targetes → aula reservada una setmana, grup de teoria que creix, aula avariada un dia i classe cancel·lada que es recupera, cada una amb què ha passat, quantes classes afecta i «Resolt» o «Resolt amb excepció».
5. [cap @ /imprevistos] Llegeix els números → concordança correcta: «1 classe afectada», «2 classes afectades», «cap de dia o hora».
6. [cap @ /imprevistos] A «Què canvia», tria un imprevist a les pastilles → la taula només mostra les classes d'aquell imprevist, amb abans i després.
7. [cap @ /imprevistos] Obre «Detall tècnic» → hi ha les excepcions per motiu i l'ordre per tornar-ho a generar.

## Part 3 · Assistent (amb la IA de prova)

Engegar l'app amb la IA de prova: `IA_PROVA=1 .venv/bin/streamlit run app/app.py` (o la configuració «part3-ia», port 8507). Amb la IA de veritat, cal `IA_URL`, `IA_CLAU` i `IA_MODEL` al `.env` de l'arrel.

1. [cap @ /] Obre l'app → baix a la dreta hi ha el botó ✦ «Assistent», i al menú ja no surt «Pregunta-ho · aviat».
2. [cap @ /] Toca «Assistent» → s'obre un plafó a la dreta amb la salutació, «Veu: Com estem avui», tres preguntes proposades i la caixa per escriure a baix.
3. [cap @ /] Toca «Quantes sessions són al torn equivocat?» → surt la pregunta i, a poc a poc, una resposta «Mode de prova» que diu la pregunta i la pantalla que veu.
4. [cap @ /part2] Ves a «Horari proposat» i obre l'assistent → «Veu:» diu la proposta i el grup triats (p. ex. «Horari proposat · 5.2 · …»), les preguntes són d'aquesta pàgina i la conversa d'abans hi és.
5. [cap @ /part2] Canvia el grup a la graella → «Veu:» canvia al grup nou.
6. [cap @ /part2] Toca el botó de fer-ho gran i després el de tornar-ho petit → ocupa tota la finestra i torna a la mida de plafó.
7. [cap @ /part2] Toca ↺ «Conversa nova» → la conversa es buida i torna la salutació.
8. [cap @ /junta] Recarrega la pàgina amb una conversa feta → la conversa es manté i només hi ha un botó «Assistent».
9. [cap @ /part2] Amb l'assistent obert, tria «Només avui» i canvia el grup → el plafó continua obert, «Veu:» canvia i la conversa es manté.
10. [cap @ /part2] Amb l'assistent obert, mira la pàgina a 1280 i a 1920 px → tot el contingut (selectors, resum i la graella fins al divendres) queda a l'esquerra del plafó, sense res tapat ni barra de desplaçament horitzontal. (reprova)
11. [cap @ /part2] Clica qualsevol lloc de la pàgina amb l'assistent obert → no es tanca; només es tanca amb la creu o amb Esc dins del plafó.

## Part 3 · Assistent (amb quiver.ai)

1. [cap @ /] Pregunta «On té classe el grup 81 dimarts?» → respon en una o dues frases, amb hores i aules, sense «Com es comprova», SQL ni llistes d'id_sessio; si diu quantes no tenen aula, en són 7 de 9. (reprova)
2. [cap @ /] Pregunta «Quina aula de 60 places està lliure dijous a les 10?» → dona les aules amb la seva capacitat en poques línies, sense SQL. (reprova)
3. [cap @ /] Pregunta «Què passa si moc la sessió <un id_sessio de la resposta 1> a les 16:00?» → comença dient que no ha aplicat ni desat cap canvi, diu què xoca de nou i que és una comprovació ràpida, diferent de la validació oficial (la 5.2 és vàlida amb relaxacions declarades). (reprova)
4. [cap @ /] Pregunta «Em recomanes un restaurant?» → diu en una frase que només ajuda amb l'horari i proposa una pregunta.
5. [cap @ /] Pregunta «¿Qué aulas hay libres el lunes a las 9?» → respon en castellà, i sota la resposta no surt cap intent fallit. (reprova)
6. [cap @ /] Mira sota la resposta del pas 1 → no hi ha cap bloc «Com es comprova» ni «Com ho he comprovat»: només el text de la resposta. (reprova)
7. [cap @ /] Pregunta «Quantes sessions de GED 3r comencen després de les 15:00 dimecres?» → respon en una frase amb el període: 14 al 2n semestre (i, si en dona dues, 1 a la setmana típica); 42 seria tot el curs. (reprova)
8. [cap @ /] Després del pas 1, pregunta «Com ho saps?» → dona els id_sessio de les classes en codi. (reprova)

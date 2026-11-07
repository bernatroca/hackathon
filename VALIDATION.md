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
4. [cap @ /] Mira les targetes de sota → n'hi ha 4, cada una amb etiqueta de color amb icona i text (Cal actuar, Vigilar o Hi cap), una xifra gran, una frase i «Proposem:». (reprova)
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

1. [cap @ /respostes] Obre «Totes les respostes» al menú → surten les 11 respostes en targetes petites.
2. [cap @ /respostes] Mira com es reparteixen → han d'anar en 2 o 3 columnes; si surten en 11 columnes estretes, anota-ho com a pendent. (reprova)
3. [cap @ /respostes] Obre «Com fem servir les aules?» → surt el plànol de les 21 aules per espina (Q1 a Q4) i planta, més fosques com més ocupades.
4. [cap @ /respostes] Passa el ratolí per sobre d'una aula del plànol → surt el codi, les places i el % d'ocupació.
5. [cap @ /respostes] Llegeix la nota sota el plànol → explica que moltes aules semblen buides perquè 3 de cada 4 classes no tenen aula a les dades.

## Opcions i menú

1. [cap @ /] Obre el desplegable «Opcions» del menú → hi ha el selector de semestre (2n per defecte) i de setmana.
2. [cap @ /] Canvia el semestre a 1r → la portada es torna a calcular sense error i les xifres canvien.
3. [cap @ /] Torna a posar el 2n semestre → tornen a sortir 2.008 i 74 %.
4. [cap @ /] Mira el menú → hi ha «Part 2 · Proposta d'horari» sense «aviat», i «Imprevistos» i «Pregunta-ho» surten marcats com «aviat». (reprova)

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

## Part 2 · Proposta d'horari

1. [cap @ /part2] Obre «Part 2 · Proposta d'horari» al menú → surt la pàgina amb el selector «Proposta», el de «Setmana de la graella» i cap error vermell.
2. [cap @ /part2] Mira el selector «Proposta» sense tocar-lo → ja surt triada la «5.1» (la més avançada), i si l'obres hi ha «Avui» i «5.1». (reprova)
3. [cap @ /part2] Tria «Avui» → les dues graelles són iguals i no surt cap classe en groc. (reprova)
4. [cap @ /part2] A «La setmana de l'estudiant» tria Gestió de Ciutats Intel·ligents, curs 1r i grup 61 → surten dues graelles costat per costat, avui i proposta, de dilluns a divendres.
5. [cap @ /part2] Tria la proposta «5.1» amb el mateix grup → les classes que avui diuen «Sense aula assignada» ara tenen aula, i cap no canvia de dia ni d'hora.
6. [cap @ /part2] Llegeix la línia de resum sota «… classes amb canvis al grup» → diu 0 canvis de dia o d'hora, els canvis d'aula, 0 canvis de torn i quantes aules diferents fa servir el grup (avui contra la proposta). (reprova)
7. [cap @ /part2] Mira una classe de 2 hores a la graella → és un sol bloc que ocupa 4 files de 30 minuts, amb l'assignatura, el tipus en paraules, les hores i l'aula; anota si el text queda massa estret quan coincideixen subgrups. (reprova)
8. [cap @ /part2] Amb la proposta «5.1» i el grup 61, llegeix «Aules diferents aquesta setmana» → anota quantes aules fa servir el grup; com més poques, millor (millora prevista de l'aula base).
9. [cap @ /part2] Baixa a «La setmana per aula» i tria l'aula Q9/5006 → surt la seva graella setmanal, sense dues classes a la mateixa hora.
10. [cap @ /part2] Clica «Descarrega l'horari de l'aula per al jurat» → es baixa un fitxer HTML que s'obre sol al navegador amb la mateixa graella.
11. [cap @ /part2] Canvia «Setmana de la graella» a la setmana del 15 de març → les dues graelles es tornen a dibuixar sense error.
12. [cap @ /part2] Llegeix tots els textos de la pàgina → no hi surten sigles tècniques sense explicar, com «R1-TORN», «PAUL» o «TE».

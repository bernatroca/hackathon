# La part 1 (anàlisi d'espais) es veu bé, s'entén per a un coordinador i les xifres quadren amb l'enunciat

## Context

- App local: http://localhost:8501 (`.venv/bin/streamlit run app/app.py`, o la configuració «app» de `.claude/launch.json`).
- L'app no té usuaris: a tots els passos l'usuari és `cap`.
- Dades: el paquet real del repte a `repte/repte-horaris-escola/paquet/`, 2n semestre per defecte. No s'ha creat cap dada nova.
- Xifres de l'enunciat que han de sortir: 2.008 classes al torn equivocat, 5.722 sense aula (74 %), 15 de 19 aules al pic, 68 % del matí i 43 amb més alumnes que places.
- Comprovació automàtica feta: `python -m nivell1.comprova` dona 18/18 i `python app/test_app.py` dona OK.

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

1. [cap @ /respostes] Obre «Totes les respostes» al menú → surten les 11 respostes en targetes petites.
2. [cap @ /respostes] Mira com es reparteixen → han d'anar en 2 o 3 columnes; si surten en 11 columnes estretes, anota-ho com a pendent.
3. [cap @ /respostes] Obre «Com fem servir les aules?» → surt el plànol de les 21 aules per espina (Q1 a Q4) i planta, més fosques com més ocupades.
4. [cap @ /respostes] Passa el ratolí per sobre d'una aula del plànol → surt el codi, les places i el % d'ocupació.
5. [cap @ /respostes] Llegeix la nota sota el plànol → explica que moltes aules semblen buides perquè 3 de cada 4 classes no tenen aula a les dades.

## Opcions i menú

1. [cap @ /] Obre el desplegable «Opcions» del menú → hi ha el selector de semestre (2n per defecte) i de setmana.
2. [cap @ /] Canvia el semestre a 1r → la portada es torna a calcular sense error i les xifres canvien.
3. [cap @ /] Torna a posar el 2n semestre → tornen a sortir 2.008 i 74 %.
4. [cap @ /] Mira el menú → «Proposta d'horari», «Imprevistos» i «Pregunta-ho» surten marcats com «aviat».

# Guió del vídeo «Com funciona l'app» (1 min 44 s)

Versió llarga del vídeo demo. Explica que hem fet una app i dedica més temps als punts que l'enunciat puntua més: nivell 1 (anàlisi, 25 %), 5.2 (torns nous, 25 %) i nivell 3 (IA, 25 %). També ensenya els punts més difícils: l'única excepció nova «demostrada», els quatre imprevistos alhora i el grau nou.

- **Vídeo:** [`demo-app.mp4`](demo-app.mp4), 1440×900, 30 fps, H.264 + AAC, **104,1 s**.
- **Muntatge reproduïble:** [`muntatge-app/index.html`](muntatge-app/index.html). Obre'l al navegador i prem «Reprodueix». `?t=50` atura el muntatge en aquest segon.
- **Captures:** [`captures-app/`](captures-app/). Són de l'app real a 1440×900, amb la IA real i les xifres finals de la Part 2 (main a `2e69fc8`).
- **Veu en off:** veu catalana del Mac (`say -v Montse -r 182`). Cada pla dura el que dura la seva frase, més 0,8 s de pausa.
- **Com es torna a fer:** amb l'app engegada al port 8511, des de l'arrel del repositori:

```bash
DPR=2 python docs/demo/eines/captura_app.py /tmp/captures-app
python docs/demo/eines/munta_app.py
MUNTATGE=muntatge-app SORTIDA=demo-app.mp4 python docs/demo/eines/render.py
```

La primera ordre deixa les captures en PNG. Per fer-les servir, cal convertir-les a JPEG dins `muntatge-app/img/`. La segona ordre genera la veu i la línia de temps (`muntatge-app/escenes.js`). La tercera fa el vídeo.

## Estructura

| Temps | Capítol | Pes a l'enunciat | Què s'hi veu |
|---|---|---|---|
| 0,0–11,6 s | Hem fet una app | — | Què és l'app i les seves parts |
| 11,6–36,0 s | Nivell 1 · Anàlisi | 25 % | Respostes, classes sense aula, «hi cabem?» i com es calcula |
| 36,0–70,1 s | Nivell 2 · Torns nous (5.2) | 25 % | Un grup que canvia de torn, el verificador oficial, la Junta i l'excepció més difícil |
| 70,1–85,6 s | 5.3 i 5.4 | 10 % + 10 % | Quatre imprevistos alhora i un grau nou |
| 85,6–99,4 s | Nivell 3 · Assistent | 25 % | Una pregunta real i la resposta amb els identificadors de les sessions |
| 99,4–104,1 s | Tancament | — | «Ho entens, ho decideixes, ho preguntes» |

Abans de cada capítol hi ha una pantalla de títol d'1,8 s, sense veu. Mentre dura el capítol, a dalt a la dreta es veu en quin nivell som.

## Plans

### 0 · Hem fet una app (0,0–5,9 s)

- **Pantalla:** títol sobre la portada desenfocada: «Hem fet una app».
- **Veu:** «Hem fet una app: Espais de l'Escola, per fer i entendre l'horari del curs vinent.»

### 1 · Les parts de l'app (5,9–11,6 s)

- **Pantalla:** portada «Com estem avui» (`a01-portada`). El cursor recorre el menú i acaba al botó «Assistent».
- **Veu:** «Té tres parts: com estem avui, l'horari proposat, i un assistent.»
- **Rètol:** «Espais de l'Escola» · «Com estem avui · Horari proposat · Resum per a la Junta · Imprevistos · Assistent».

### 2 · Totes les respostes (13,4–19,0 s) · Nivell 1

- **Pantalla:** «Totes les respostes» (`a02-respostes`). Zoom a la primera fila; el cursor fa clic a «Com ho sabem →».
- **Veu:** «Primer, l'anàlisi: onze respostes, de la més urgent a la menys.»
- **Rètol:** «11 respostes, les urgents primer».
- **Font:** l'app («Es mostren 11 de 11»).

### 3 · Classes sense aula (19,0–24,6 s) · Nivell 1

- **Pantalla:** detall «Classes sense aula» (`a03-sense-aula`), amb marcs a «Què vol dir».
- **Veu:** «Avui, tres de cada quatre classes no tenen aula assignada.»
- **Rètol:** «5.722 classes sense aula (74 %)» · «4.541 cal assignar-les de debò · 919 són laboratoris · 262, dobles sense aula pròpia».
- **Font:** l'app: «aproximadament el 73,9 % de les classes (5.722 classes)» i «4.541 per assignar de debò · 919 laboratoris · 262 dobles».

### 4 · Hi cabem? (24,6–31,4 s) · Nivell 1

- **Pantalla:** detall «Si 1r i 2n fan classe al matí, hi cabem?» (`a04-hi-cap`). Marcs a la graella d'aules i a «15 ocupades».
- **Veu:** «Si primer i segon passen al matí, hi cabem? Sí: quinze aules de dinou, a l'hora punta.»
- **Rètols:** primer «1r i 2n al matí: hi cabem?». Després «Sí, hi cap: 15 de 19 aules» · «A l'hora més plena del matí, i encara queden 2 aules de reserva».
- **Font:** l'app: «19 aules disponibles: 15 ocupades al moment més ple i 4 lliures. A part, 2 aules de reserva».

### 5 · Com ho hem calculat (31,4–36,0 s) · Nivell 1

- **Pantalla:** el mateix detall, a «Com ho hem calculat», amb la consulta SQL oberta (`a05-hi-cap-calcul`).
- **Veu:** «I cada xifra explica com s'ha calculat.»
- **Rètol:** «Cada xifra, amb el seu càlcul» · «En paraules planeres i, per a qui ho vulgui, la consulta SQL».

### 6 · Un grup canvia de torn (37,8–42,7 s) · 5.2

- **Pantalla:** «Horari proposat», proposta «Torns nous (5.2)», Enginyeria Química, 3r, grup 21 (`a06-p2-grup`). Marcs als selectors i a «8 canvis d'hora».
- **Veu:** «Amb els torns nous, tercer de Química passa del matí a la tarda.»
- **Rètol:** «3r de Química: del matí a la tarda» · «8 classes canvien d'hora aquesta setmana, i totes tenen aula».
- **Font:** l'app: «La proposta assigna aula a 8 classes que no en tenien» · «8 canvis d'hora».

### 7 · Cada canvi, a la vista (42,7–47,5 s) · 5.2

- **Pantalla:** la graella del grup a la tarda (`a07-p2-graella`). Zoom a dijous i marc a «Abans: dijous 09:30».
- **Veu:** «Cada classe diu on era abans.»
- **Rètol:** «Cada canvi, a la vista» · «"Abans: dijous 09:30" · ara dijous a les 14:30, a la Q1/1011».

### 8 · Verificador oficial (47,5–56,4 s) · 5.2

- **Pantalla:** sortida real del verificador oficial per a `resultats/nivell2/5.2/proposta.csv` amb les relaxacions (`a08-verificador`). Marcs al veredicte, a R5-SENSE-AULA i a R1-TORN.
- **Veu:** «El verificador oficial, el del jurat, la valida: totes les classes tenen aula, i les excepcions, declarades.»
- **Rètol:** «VALIDA AMB RELAXACIONS DECLARADES» · «Classes sense aula: 4.541 → 0 · fora de torn: 2.008 → 0, amb 459 excepcions declarades».
- **Font:** `python -m horaris check … --semestre 2 --relaxacions …` (0,7 s) i `resultats/nivell2/5.2/xifres.csv`.
- **Matís:** «totes les classes tenen aula» vol dir les que en necessiten. Els laboratoris PLAB no es toquen i els dobles sense espai propi no en necessiten (R5-SENSE-AULA no els compta).

### 9 · Resum per a la Junta (56,4–62,2 s) · 5.2

- **Pantalla:** «Resum per a la Junta», proposta «Horari complet (5.2)» (`a09-junta`). Marc a les dues primeres fitxes.
- **Veu:** «La Junta ho té en una pàgina: quinze aules de dinou al matí, divuit a la tarda.»
- **Rètol:** «La Junta decideix amb una pàgina» · «Hora punta de matí i tarda, cursos afectats i excepcions · resum A4 descarregable».

### 10 · El cas més difícil (62,2–70,1 s) · 5.2

- **Pantalla:** la mateixa pàgina, a «Excepcions als torns» (`a10-junta-excepcions`). Marc a la línia de S04526.
- **Veu:** «El cas més difícil: una classe de la setmana d'avaluació no té cap tarda lliure. Ho demostrem, i ho declarem.»
- **Rètol:** «1 excepció nova, demostrada» · «S04526, divendres 9/4. Les altres 458 són classes fixades que ja són a la tarda».
- **Per què ho ensenyem:** la regla 11 de l'enunciat demana distingir «no hem trobat un horari vàlid» de «hem demostrat que no existeix».

### 11 · Quatre imprevistos alhora (71,9–80,5 s) · 5.3

- **Pantalla:** «Imprevistos» (`a11-imprevistos`). Marc a «Comprovat amb el verificador oficial».
- **Veu:** «Quatre imprevistos alhora: aula reservada, grup que creix, avaria i classe cancel·lada. Es resol amb pocs canvis.»
- **Rètol:** «65 classes canvien d'aula, 1 de dia» · «Comprovat amb el verificador oficial · 28 segons de càlcul».
- **Matís:** diem «pocs canvis» i no «el mínim» perquè el resultat és òptim dins el model de reparació local, no per a tot l'horari. El verificador compta 64 canvis d'aula, perquè no compta la classe cancel·lada.

### 12 · Un grau nou hi cap (80,5–85,6 s) · 5.4

- **Pantalla:** targeta «Un grau nou de 40 places» de la portada (`a12-grau-nou`).
- **Veu:** «I un grau nou de quaranta places hi cap, sense moure cap classe.»
- **Rètol:** «Un grau nou de 40 places hi cap» · «235 sessions noves · 0 classes del 5.2 mogudes · verificador oficial».
- **Font:** l'app i `resultats/nivell2/5.4/xifres.csv` (`canvis_franja_vs_referencia 0`, `canvis_aula_vs_referencia 0`).

### 13 · La pregunta a l'assistent (87,4–93,6 s) · Nivell 3

- **Pantalla:** la graella del grup 21. El cursor fa clic a «Assistent», s'escriu la pregunta, surt «Pensant…» i la resposta s'escriu (`a13-assistent-00` a `-16`).
- **Veu:** «I l'assistent: on té classe aquest grup, dijous?»
- **Pregunta escrita:** «On té classe el grup 21 de 3r de Química dijous, a la proposta 5.2? Digues-me quines sessions són.»
- **Rètol:** «"On té classe el grup 21 de 3r de Química dijous?"» · «Sap què hi ha a la pantalla: proposta 5.2 · GEQ 3r · grup 21». El plafó ho mostra a «Veu: Horari proposat · 5.2 · GEQ 3r 21».
- **Nota de muntatge:** amb la IA real, la resposta va trigar 7,0 s. Al vídeo l'espera dura 1,75 s.

### 14 · Una resposta que es pot comprovar (93,6–99,4 s) · Nivell 3

- **Pantalla:** zoom al plafó i a la columna de dijous. Marc a «S00086 i S11829».
- **Veu:** «Respon amb les dades, i diu quines sessions són, perquè ho puguis comprovar.»
- **Rètol:** «S00086 i S11829, a la Q1/1011» · «Cada resposta surt d'una consulta a les dades; avui eren al matí».
- **Comprovat:** a `resultats/nivell2/5.2/proposta.csv`, S00086 és `J,14:30,Q1/1011` i S11829 és `J,16:30,Q1/1011`. A `paquet/sessions.csv` (avui) són dijous a les 09:30 i a les 08:30.

### 15 · Tancament (99,4–104,1 s)

- **Pantalla:** «Ho entens, ho decideixes, ho preguntes».
- **Veu:** «Espais de l'Escola: l'horari, comprovat i explicat.»

## Resposta real de l'assistent (gravada)

> Dijous, a la setmana típica del 2n semestre de la proposta 5.2, el grup 21 té dues sessions a la **Q1/1011**: 14.30–16.30 (102435) i 16.30–17.30 (106051). Són les sessions `S00086` i `S11829`.

## Per al torn de preguntes

- **«Com ho saps?» en un missatge a part no funciona bé.** L'assistent no conserva el resultat de l'eina d'un torn a l'altre. Si el jurat vol els identificadors, cal demanar-los a la mateixa pregunta, com fa el vídeo («Digues-me quines sessions són»).
- **Els «què passa si…» poden fallar.** Amb «Què passa si a la proposta 5.2 passo al matí les classes de dijous del grup 21 de 3r de Química?», l'assistent ha respost que no reconeixia el grup «21» per moure'l. Per això el vídeo no ensenya aquest cas.
- **La pregunta de l'enunciat** («Quina aula de 60 places està lliure dijous a les 10?») funciona. Amb «a la proposta 5.2» respon Q4/0003 (90 places) i Q3/1007 (130 places). Sense dir la proposta, consulta l'horari d'avui.

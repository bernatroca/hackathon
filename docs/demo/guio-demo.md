# Guió del vídeo demo general (30,0 s)

**Espais de l'Escola**: horaris i aules 2027-28 de l'Escola d'Enginyeria, per al tècnic de Gestió Acadèmica que avui fa els horaris a mà.

- **Vídeo:** [`demo-general.mp4`](demo-general.mp4), 1440×900, 30 fps, H.264 + AAC, **30,0 s**.
- **Muntatge reproduïble:** [`muntatge/index.html`](muntatge/index.html). Obre'l al navegador i prem «Reprodueix». `?t=12.5` atura el muntatge en aquest segon.
- **Captures:** [`captures/`](captures/), numerades en l'ordre del vídeo. Són de l'app real a 1440×900, arrencada des d'aquest worktree i amb la IA real.
- **Veu en off:** veu catalana del Mac (`say -v Montse -r 185`). Si la presentació vol veu humana, cal llegir el mateix text amb els mateixos temps.
- **Com es torna a fer:** [`eines/`](eines/) (captures amb Chromium sense finestra, render fotograma a fotograma i ffmpeg).

## La història en tres actes

| Acte | Temps | Missatge |
|---|---|---|
| 1 · El problema | 0,0–9,8 s | Avui 5.722 classes no tenen aula. Si 1r i 2n passen al matí, hi cabem? |
| 2 · La solució | 9,8–21,2 s | Sí. La proposta (5.1–5.4) passa el verificador oficial: aules, torns, imprevistos i grau nou. |
| 3 · El valor | 21,2–30,0 s | Gestió Acadèmica ho entén, la Junta decideix en una pàgina i l'assistent respon preguntes reals. |

## Plans

Els temps són d'inici i final del pla. La veu comença uns 0,1–0,3 s després que el pla.

### Pla 0 · Portada del vídeo (0,0–2,6 s)

- **Pantalla:** la portada «Com estem avui», enfosquida i desenfocada, amb el títol a sobre.
- **Veu en off (0,3–2,4 s):** «Gestió Acadèmica fa els horaris a mà.»
- **Text sobreimprès:** «Espais de l'Escola» · «Horaris i aules 2027-28 · Escola d'Enginyeria».
- **Clic o moviment:** cap. Fosa cap al pla 1.

### Pla 1 · Avui, classes sense aula (2,6–6,8 s) · Acte 1

- **Pantalla:** «Com estem avui» → «Classes sense aula» → «Com ho sabem →», apartat «Què vol dir» (captura `01-sense-aula-detall.png`).
- **Veu en off (2,8–6,5 s):** «Avui, cinc mil set-centes vint-i-dues classes no tenen aula.»
- **Text sobreimprès:** «5.722 classes sense aula» · «74 % del semestre, segons les dades d'avui».
- **Clic o moviment:** zoom lent cap a «Què vol dir» i marc sobre la línia «… (5.722 classes)».
- **Font de la xifra:** l'app, a «Classes sense aula»: «aproximadament el 73,9 % de les classes (5.722 classes)».

### Pla 2 · La pregunta del model nou (6,8–9,8 s) · Acte 1

- **Pantalla:** portada «Com estem avui», targeta gran «Si 1r i 2n fan classe al matí, hi cabem?» (`02-portada.png`).
- **Veu en off (6,95–9,7 s):** «I si primer i segon passen al matí, hi cabem?»
- **Text sobreimprès:** «1r i 2n al matí: hi cabem?»
- **Clic o moviment:** zoom suau cap a la pregunta.

### Pla 3 · Sí, hi cap (9,8–13,0 s) · Acte 2

- **Pantalla:** la mateixa targeta. Zoom a la graella d'aules: «15 ocupades · 4 lliures · 2 de reserva».
- **Veu en off (9,9–12,9 s):** «Sí: quinze de dinou aules, a l'hora més plena.»
- **Text sobreimprès:** «Sí: 15 de 19 aules a l'hora punta» · «21 aules, 2 de reserva per a imprevistos».
- **Clic o moviment:** zoom a la graella i marc sobre «15 ocupades».
- **Font:** portada de l'app i «Resum per a la Junta» (matí, hora més plena: 15 de 19 aules).

### Pla 4 · Proposta verificada (13,0–17,6 s) · Acte 2

- **Pantalla:** «Horari proposat», setmana del grup 61 de Gestió de Ciutats Intel·ligents i Sostenibles (13,0–15,3 s, `03-horari-grup.png`). Després «Consulta una aula», aula Q2/1005 (15,3–17,6 s, `04-horari-aula-Q2-1005.png`).
- **Veu en off (13,1–17,4 s):** «La proposta dona aula a cada classe. El verificador oficial ho valida.»
- **Text sobreimprès:** «Validat amb el verificador oficial» · «5.1: 4.541 → 0 classes per assignar · 5.2: torns nous, 459 excepcions declarades».
- **Clic o moviment:** marc sobre «La proposta assigna aula a 15 classes que no en tenien». Fosa a la graella de l'aula, amb un desplaçament lent.
- **Fonts:** `resultats/nivell2/5.1/xifres.csv` (veredicte `NO VALIDA → VALIDA`, `R5-SENSE-AULA 4541 → 0`). `resultats/nivell2/5.2/xifres.csv` (veredicte `VALIDA AMB RELAXACIONS DECLARADES`, `R1-TORN 2008 → 0`, `incompliments_declarats 459`). Les 4.541 són les classes que cal assignar de debò: l'app ho explica a «Classes sense aula» («4.541 per assignar de debò · 919 laboratoris · 262 dobles»).

### Pla 5 · Imprevistos i grau nou (17,6–21,2 s) · Acte 2

- **Pantalla:** «Imprevistos» (17,6–19,4 s, `05-imprevistos.png`). Després la targeta «Un grau nou de 40 places» de la portada (19,4–21,2 s, `06-portada-grau-nou.png`).
- **Veu en off (17,75–21,0 s):** «També resol imprevistos, i hi fa cabre un grau nou.»
- **Text sobreimprès:** «5.3 · Imprevistos: 65 classes canvien d'aula, 1 d'hora» · «5.4 · Grau nou: 235 sessions, 0 classes del 5.2 mogudes».
- **Clic o moviment:** marc sobre «Comprovat amb el verificador oficial». Fosa i zoom a la targeta del grau nou.
- **Fonts:** pantalla «Imprevistos» (65 canvis d'aula, 1 de dia o hora). `resultats/nivell2/5.4/xifres.csv` (`sessions_52_mogudes 0`, `sessions_grau_nou_fora_franja 41`). La portada diu «hi col·loca 235 sessions».

### Pla 6 · Resum per a la Junta (21,2–24,0 s) · Acte 3

- **Pantalla:** «Resum per a la Junta» amb la proposta «Horari complet (5.2)»: les quatre fitxes (`07-junta.png`).
- **Veu en off (21,35–23,7 s):** «La Junta decideix amb una sola pàgina.»
- **Text sobreimprès:** «La Junta decideix en una pàgina» · «Resum A4 descarregable».
- **Clic o moviment:** zoom a les quatre fitxes (15 de 19 · 18 de 19 · 100 % · 459 classes).

### Pla 7 · L'assistent (24,0–30,0 s) · Acte 3

- **Pantalla:** portada amb el botó «Assistent» (baix a la dreta) → s'obre el plafó → s'escriu la pregunta → «Pensant…» → resposta (captures `08-assistent-00` a `08-assistent-14`).
- **Veu en off (24,1–27,6 s):** «I l'assistent respon preguntes reals, amb dades de l'horari.»
- **Text sobreimprès:** «"Quina aula de 60 places està lliure dijous a les 10?"». Quan surt la resposta: «Q2/1005, 63 places, i 9 aules més». Al final (28,4–30,0 s): «Espais de l'Escola · ho entens, ho decideixes, ho preguntes».
- **Clic o moviment:** el cursor va al botó «Assistent» i hi fa clic (24,6 s). S'escriu la pregunta (24,85–26,35 s) i s'envia amb Retorn. La resposta surt a les 27,25 s. Zoom al plafó i marc sobre «Q2/1005, 63 places».
- **Nota de muntatge:** amb la IA real, la resposta va trigar 6,2 s. Al vídeo l'espera dura 0,9 s.

## Resposta real de l'assistent (gravada)

> Dijous 4 de febrer, de 10 a 11, tens lliures: Q2/1005, 63 places · Q4/1013, 88 places · Q2/1009, 90 places · Q2/1013, 90 places · Q4/0003, 90 places · Q3/1003, 100 places · Q4/0007, 117 places · Q3/1007, 130 places · Q3/1011, 130 places · Q1/1011, 160 places

**Per al torn de preguntes:** l'assistent consulta per defecte l'horari d'**avui** (`proposta='avui'`). A les dades d'avui, el 74 % de les classes no té aula, i per això moltes aules hi surten lliures. A la proposta 5.2, en canvi, la Q2/1005 té classe dijous de 09:30 a 10:30 (és el pla 4 del vídeo) i queda lliure a partir de les 10:30. Si el jurat ho pregunta, es pot repetir la pregunta afegint «a la proposta 5.2».

## Text sencer de la veu en off

> Gestió Acadèmica fa els horaris a mà. Avui, cinc mil set-centes vint-i-dues classes no tenen aula. I si primer i segon passen al matí, hi cabem? Sí: quinze de dinou aules, a l'hora més plena. La proposta dona aula a cada classe. El verificador oficial ho valida. També resol imprevistos, i hi fa cabre un grau nou. La Junta decideix amb una sola pàgina. I l'assistent respon preguntes reals, amb dades de l'horari.

Són 24,9 s de veu dins de 30,0 s de vídeo.

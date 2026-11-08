# Plantilla del PPTX · 3 minuts

Presentació al jurat de diumenge. Segueix l'ordre que recomana la nostra guia ([2-Ja-tenim-la-idea.pdf](pdf/2-Ja-tenim-la-idea.pdf), apartats 10 i 11, amb els consells del vídeo d'en Zahur): **qui som, la persona i el seu problema, la prova, el cost, la solució, la demo, l'abans → després, com ho hem fet i els propers passos.** L'organització demana una demo: serà un **vídeo de 90 s** dins la presentació (diapositiva 5). No s'explica per nivells del repte: els nivells surten dins la demo i a les reserves.

- **Durada:** 3 minuts. **8 diapositives**; el vídeo de la demo n'ocupa la meitat (90 s).
- **Persona:** el tècnic de Gestió Acadèmica que fa i manté l'horari.
- **Xifres:** totes surten de [RESUM-PRESENTACIO.md](RESUM-PRESENTACIO.md) i dels `informe.json`/`resum.json` de `resultats/nivell2/`. Si una xifra no hi és, no va a la diapositiva.

## Què demana l'entrega (correu de l'organització, dg 8-11)

- **Hora límit: avui a les 12:00**, a la plataforma, des de l'enllaç personal de qualsevol membre (pestanya «Entrega»). Fins a les 13:00 s'accepta amb un 10 % de penalització. Es pot corregir fins a l'hora límit: compta l'última versió.
- **Repte, nom del projecte i un resum curt.** El jurat llegeix el resum **abans** de la presentació de 3 minuts: la diapositiva 2 no ha de repetir-lo, només posar-hi cara (la persona i la pregunta al públic).
- **Un sol .zip de fins a 100 MB** amb el codi, la demo i la presentació. Sense `node_modules` ni dades pesades. Si la demo pesa massa, se'n posa l'enllaç.
- **Acceptar l'avís de propietat intel·lectual** i prémer «Envia l'entrega».
- **Galeria pública (opcional):** una casella a la mateixa pestanya. Hi surt només el projecte, mai el codi ni el zip. Si la marquem, a la pestanya «Galeria» hi ha un esborrany fet amb IA que cal revisar abans de publicar.

### Proposta de nom i resum (per revisar)

- **Nom:** «Espais de l'Escola · horaris 2027-28» (el títol de l'app).
- **Resum curt:**

  > Una app per al tècnic de Gestió Acadèmica de l'Escola d'Enginyeria que ha de fer l'horari 2027-28 amb el model nou de torns. Diu com estem avui (l'horari actual no passa el verificador oficial: 2.008 classes al torn equivocat i 4.541 sense aula) i proposa horaris que sí que el passen: aules (5.1), horari complet del 2n semestre (5.2), quatre imprevistos (5.3) i un grau nou de 40 places, que hi cap sense moure cap classe (5.4). Un assistent respon preguntes sobre l'horari amb les dades. Fet per l'equip Neo amb Claude Code i subagents de Codex.

### Què va dins el .zip

| Carpeta del zip | Què hi va | Mida aproximada |
|---|---|---|
| `codi/` | El repositori de `main` (`git archive`), sense `.venv`, `node_modules` ni les carpetes de dades | ~2 MB |
| `propostes/` | `lliurament-nivell2.zip` (propostes 5.1-5.4 amb els informes del verificador) | petit |
| `demo/` | `demo-general.mp4` (30 s, 13 MB) i, si cal, `demo-app.mp4` (17 MB) | ~30 MB |
| `presentacio/` | El `.pptx` i una còpia en PDF | — |
| arrel | `README.md`: com s'executa, què hi ha a cada carpeta i els models d'IA fets servir | — |

## Les 3 preguntes que ha de respondre

| Pregunta | On es respon |
|---|---|
| Quin problema resolem i per a qui? | Diapositiva 2 |
| Com sabem que és real? | Diapositiva 3 |
| Per què funciona la nostra solució? | Diapositives 5 i 6 (la demo i l'abans → després amb números) |

## Diapositiva per diapositiva

| # | Diapositiva | Què ha de tenir | Temps |
|---|---|---|---|
| 1 | **Qui som** | Portada amb Horaris i espais 2027-28 · Escola d'Enginyeria UAB · UAB THE HACK! 2026. Equip Neo: noms i una frase de cadascú, i què ens ha portat a triar aquest repte. | 15 s |
| 2 | **La persona i el seu problema** | Obrir amb una pregunta al públic: «Qui ha hagut de quadrar un horari a mà?». La persona en una frase: el tècnic de Gestió Acadèmica ha de fer l'horari del curs 2027-28 amb el model nou de torns (1r i 2n al matí, 3r i 4t a la tarda) i les aules que hi ha. | 15 s |
| 3 | **La prova** | 1-2 xifres amb la font a sota: l'horari d'avui **no passa el verificador oficial** del repte; **2.008** classes queden al torn equivocat i **4.541** no tenen aula. Font: verificador oficial del repte (`resultats/nivell2/5.2/xifres.csv`, columna «abans»). | 15 s |
| 4 | **El cost i la solució** | Cost, en una frase i sense inventar: tal com està, l'horari no es pot publicar, i cada canvi a mà pot trencar una altra regla (aula ocupada, docent a dos llocs, torn equivocat). **Solució en una frase, sense paraules tècniques:** «Una app que diu com estem, proposa un horari que compleix totes les regles i respon preguntes.» | 10 s |
| 5 | **Demo (vídeo de 90 s)** | El vídeo incrustat a pantalla completa, que s'engega amb un clic. És un sol pla fluid de l'app, sense talls, que segueix el recorregut del tècnic i deixa veure com canvien les coses (guió a [GUIO-VIDEO-DEMO.md](GUIO-VIDEO-DEMO.md)). Qui presenta parla per sobre del vídeo. | 90 s |
| 6 | **Abans → després** | Dues columnes amb números. **Abans:** horari NO VALIDA, 2.008 fora de torn, 4.541 sense aula. **Després:** 4 de 4 propostes vàlides al verificador oficial (excepcions declarades amb motiu), 0 fora de torn i 0 sense aula al 5.2, la rutina setmanal es manté alta (99,7 % → 95,6 %: baixa una mica, i es diu), i un grau nou de 40 places hi cap (235 de 235 sessions) sense moure cap classe. | 15 s |
| 7 | **Com ho hem fet** | Una sessió de Claude Code (Claude Opus 5.5) orquestra i subagents de Codex (`gpt-6.1-sol`) programen per rols, cadascun al seu worktree, amb revisors abans d'unir res. Una frase sobre el problema més difícil i com el vam resoldre (per exemple, on van els alumnes dels dobles graus, buscat a la web de la UAB). | 10 s |
| 8 | **Propers passos** | Una idea de [MILLORES-PITCH.md](MILLORES-PITCH.md): l'alumnat veu «El meu horari» amb els canvis, i el professorat demana canvis que Gestió Acadèmica aprova amb un clic, ja validats. Gràcies. | 10 s |

Total: 180 s. Si l'assaig s'allarga, es retalla la diapositiva 4 (el cost passa a les notes) i la 7 queda en una sola frase. El vídeo de la demo no es retalla: és el que el jurat recorda.

## Normes per a totes les diapositives

- **Una idea per diapositiva**, i el títol diu la conclusió.
- **Una xifra gran** com a molt, amb l'unitat. Màxim 20 paraules visibles: amb 3 minuts no hi ha temps de llegir.
- **Lletra:** títol ≥ 32 pt, text ≥ 20 pt, xifra gran ≥ 60 pt. Res de taules ni codi a les diapositives que es presenten.
- **Colors i lletres de l'app:** fons crema `#F4F3EF`, text `#0B0B0B`, blau `#2A78D6`; pastilles d'estat verd `#1F6B33` sobre `#E9F4EC` («hi cap»), groc `#8A5C00` sobre `#FFF5DC` («vigilar»), vermell `#A12C2C` sobre `#FBE9E9` («cal actuar»).
- **Captures de l'app** en lloc de gràfics nous: el jurat ha de reconèixer el que veurà a la demo.
- **Notes de qui parla** a cada diapositiva: què es diu, qui ho diu i la font de cada xifra.

## Diapositives de reserva (després de la 8, per a les preguntes del jurat)

- **R1 · Part 1 · Com estem avui:** matí 70 % i tarda 42 %, 74 % sense aula (4.541 per assignar de debò), grau nou 26 h de 181 h lliures, 8 tipus de problemes, 25 de 25 comprovacions.
- **R2 · Part 2 · Les quatre propostes:** 5.1 VALIDA; 5.2, 5.3 i 5.4 VALIDA AMB RELAXACIONS DECLARADES, i què vol dir una relaxació.
- **R3 · 5.2 · Què guanyem i què costa:** aules de teoria extra per grup 14 → 3; hores mortes i desplaçaments d'aula pugen; 459 excepcions = 458 fixades que la regla 1 no deixa moure + 1 de la setmana d'avaluació.
- **R4 · Escenaris:** 5.3, quatre imprevistos amb 64 canvis d'aula i 0 canvis de torn; 5.4, 235 de 235 sessions i 41 fora de la seva franja (mínim demostrat).
- **R5 · Junta:** pic del matí 15 de 19 aules, tarda 18 de 19; recomanem deixar 1-2 aules lliures a l'hora punta.
- **R6 · Com sabem que és correcte:** verificador oficial (4 de 4), cap alumne ni docent a dos llocs alhora, revisió per agents (`docs/REVISIO-PUNT5.md`).
- **R7 · L'assistent (part 3):** què respon, que no toca l'horari i que diu d'on surt cada resposta.
- **R8 · Ús d'IA i fonts:** models i versions (com al README) i la taula de fonts de cada xifra.

## Davant del jurat

- Escolteu cada pregunta sencera. No discutiu.
- Si una cosa no està feta, digueu-ho: «No ens ha donat temps. És el següent pas.» El jurat penalitza molt les mentides.
- Les excepcions declarades es diuen com a excepcions, mai com a «sense errors».

## Abans de lliurar (dg, abans de les 12:00; com a tard 13:00 amb penalització)

- [ ] Xifres de les diapositives 3 i 6 contrastades amb els `informe.json`/`resum.json` finals de `main`.
- [ ] Captures fetes amb l'app de `main` (no amb un servidor antic).
- [ ] Vídeo de la demo (90 s) incrustat a la diapositiva 5 i provat a l'ordinador de la presentació.
- [ ] Assaig de qui parla per sobre del vídeo, sincronitzat amb el guió.
- [ ] L'app oberta en una altra pestanya, per si el jurat demana veure alguna cosa en directe.
- [ ] Notes de qui parla a totes les diapositives, i qui diu cada part.
- [ ] Exportat a **.pptx**, i una còpia en PDF.
- [ ] Nom i resum curt revisats per l'equip i escrits a la plataforma.
- [ ] Zip muntat (codi, propostes, demo, presentació, README), de menys de 100 MB i sense dades pesades ni `node_modules`.
- [ ] Entrega enviada abans de les 12:00, i decidit si sortim a la galeria pública.
- [ ] Assaig cronometrat: 3 minuts o menys.

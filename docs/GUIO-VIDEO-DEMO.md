# Guió del vídeo demo · 90 s

L'organització demana una demo dins la presentació de 3 minuts. Serà aquest vídeo, a la diapositiva 5 de la [plantilla del PPTX](PLANTILLA-PPTX.md). També va al .zip de l'entrega (carpeta `demo/`).

## Com ha de ser

- **Durada: 90 s** (com a molt 95 s).
- **Fluid tota l'estona:** un sol pla continu de l'app de debò, gravat mentre s'hi treballa. Sense captures fixes encadenades ni talls secs. El cursor es veu i es mou a poc a poc, el desplaçament és suau i els clics deixen veure **com canvia** la pantalla: un filtre que s'activa, un horari que es redibuixa, una targeta que passa a verd, la resposta de l'assistent que apareix.
- Si cal ajuntar dues preses, que sigui amb una fosa de menys de 0,5 s i sempre en un moment en què la pantalla quedi igual.
- **Mida:** 1920×1080 (o 1440×900), 30 fps, H.264, menys de 30 MB.
- **Sense veu en off:** qui presenta parla en directe per sobre. Rètols curts a baix (màxim 6-8 paraules, 2-3 s cadascun) perquè s'entengui també sense so. Si sobra temps, se'n pot fer una segona versió amb veu per al zip.
- **App de `main`**, arrencada just abans de gravar, amb la finestra neta: sense pestanyes, notificacions ni barra de favorits. Zoom del navegador perquè el text es llegeixi a la pantalla del jurat.
- **Ritme:** cada pas dura prou perquè el jurat llegeixi la xifra clau abans de passar al següent. Millor ensenyar menys coses i ben vistes.

## El recorregut (el tècnic de Gestió Acadèmica fent la seva feina)

| Temps | Pantalla | Què es veu canviar | Rètol |
|---|---|---|---|
| 0-12 s | **Com estem avui** | Entra la portada. El cursor passa pel bloc gran «Si 1r i 2n fan classe al matí, hi cabem?» → «Sí, hi cap», en verd, amb els 19 quadrets d'aules. Baixa a les quatre caixes (2.008 al torn equivocat, 74 % sense aula, grau nou: hi cap). | «Com estem avui, en una pantalla» |
| 12-20 s | **Com ho sabem** | Clic a «Com ho sabem →» del bloc gran: s'obre el detall amb el gràfic i l'explicació planera. Torna a la portada. | «Cada xifra diu com s'ha calculat» |
| 20-42 s | **Horari proposat** | Tria un grup: apareix l'horari de la setmana. Es veu què canvia respecte d'avui (canvi d'hora, aula nova). Clic a una pastilla de filtre: les classes que hi encaixen queden ressaltades. Obre una classe per veure'n el detall. | «L'horari nou, grup per grup» |
| 42-54 s | **Terminal · verificador oficial** | Fosa curta cap a un terminal a pantalla completa, amb lletra gran. S'escriu l'ordre del jurat: `python -m horaris check ../../resultats/nivell2/5.2/proposta.csv --semestre 2 --relaxacions ../../resultats/nivell2/5.2/relaxacions.csv` i surt **VALIDA AMB RELAXACIONS DECLARADES**. Si hi ha temps, abans es passa `python -m horaris check paquet/proposta_partida.csv --semestre 2` (l'horari d'avui) i surt **NO VALIDA**, per veure el canvi. Fosa de tornada a l'app. | «La mateixa ordre que farà servir el jurat» |
| 54-63 s | **Imprevistos** | Tria un imprevist (per exemple, una aula tancada): surten les classes afectades i on van ara, amb el mínim de canvis. | «Un imprevist, el mínim de canvis» |
| 63-72 s | **Resum per a la Junta** | El resum d'una pàgina: aules ocupades a l'hora punta (matí 15 de 19, tarda 18 de 19) i el grau nou que hi cap. | «La Junta decideix amb una pàgina» |
| 72-86 s | **Pregunta-ho (assistent)** | S'escriu una pregunta real, provada abans perquè l'assistent la respongui bé. Apareix la resposta. Es pregunta «Com ho saps?» i diu d'on surt. | «Pregunta amb les teves paraules» |
| 86-90 s | **Tancament** | Torna a «Com estem avui», amb el bloc verd «Sí, hi cap». Fosa a negre amb «Espais de l'Escola · Equip Neo». | — |

Si el vídeo s'allarga, es retalla primer «Com ho sabem» i després la Junta. L'horari proposat, el **verificador al terminal** (l'enunciat de la part 2 ho demana) i l'assistent no es retallen. «Totes les respostes» ja no hi surt: no hi cap en 90 s.

## Abans de donar-lo per bo

- [ ] Dura 90 s (com a molt 95) i no té cap tall sec.
- [ ] Es veu el terminal amb l'ordre `python -m horaris check` i el veredicte, prou gran per llegir-lo.
- [ ] Totes les xifres que surten coincideixen amb les de la presentació (diapositives 3 i 6).
- [ ] Es llegeix bé en un projector: text gran, sense finestres ni notificacions.
- [ ] Exportat a `.mp4` (menys de 30 MB) i incrustat a la diapositiva 5 del PPTX.
- [ ] Còpia a la carpeta `demo/` del zip de l'entrega.

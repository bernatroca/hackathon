# Vídeo demo de 90 s per a la presentació

Vídeo de la diapositiva 5 i de la carpeta `demo/` de l'entrega: [`demo-90s.mp4`](demo-90s.mp4), **82,1 s**, gravat amb el codi de `main` 0556bc7. Tots els rètols, amb imatge i temps: [`retols-demo-90s.html`](retols-demo-90s.html). Segueix [`docs/GUIO-VIDEO-DEMO.md`](../GUIO-VIDEO-DEMO.md).

- **Un sol pla continu de l'app de debò,** arrencada just abans de gravar amb el codi de `main`. La finestra de terminal entra i surt amb una fosa de 0,45 s.
- **El cursor es mou a poc a poc i el desplaçament és suau.** Es veu canviar la pantalla a cada clic: el detall que s'obre, un altre grup que es redibuixa, «Mira l'exemple», la pastilla «Canvia», el detall d'una classe, l'imprevist que filtra la taula la resposta de l'assistent i el seu «Comprova-ho».
- **Sense veu en off.** El vídeo s'entén sol:
  - a dalt a la dreta, una etiqueta diu sempre quina part del repte s'està resolent;
  - a baix, un rètol diu la part, què es veu i què hi tenim en compte.
- **Format:** 1920×1080 (la pàgina fa 1440×810 punts amb escala 4/3, perquè el text es llegeixi en un projector), 30 fps, H.264, sense so.

## Recorregut

| Tram | Pantalla | Part del repte | Rètol (què es veu · què hi tenim en compte) |
|---|---|---|---|
| Portada | Com estem avui | Nivell 1 · Anàlisi | «1r i 2n al matí: sí, hi cabem» · 15 de 19 aules a l'hora més plena, i en guardem 2 de reserva. «Avui → amb la proposta» · 2.008 fora de torn → 459 excepcions declarades; 4.541 sense aula → 0 |
| Detall | «Mira el detall de les aules →» | Nivell 1 · Com ho sabem | «Cada xifra explica com s'ha calculat» · sense laboratoris ni dobles titulacions, que no necessiten aula pròpia |
| Horari proposat | «Mira l'horari proposat →», un altre curs (4t), «Mira l'exemple» (grup 430), pastilla «Canvia», detall de Computació d'Altes Prestacions | Nivell 2 · 5.2 Torns nous | «1r i 2n al matí; 3r i 4t a la tarda» · cada grup veu què canvia respecte d'avui. «Cada classe diu on era abans» · dijous 12:30 → dijous 14:30, a la Q3/0009 |
| Terminal | Verificador oficial, des de `repte/repte-horaris-escola` | Nivell 2 · Verificador oficial | «La mateixa ordre que farà servir el jurat» · horari d'avui NO VALIDA → proposta 5.2 VALIDA, amb 459 excepcions declarades i justificades |
| Imprevistos | Resum dels quatre imprevistos i «Mira l'exemple» | Nivell 2 · 5.3 Imprevistos | «Quatre imprevistos alhora, pocs canvis». «Aula avariada un dia: 6 classes canvien d'aula» · mateix dia i hora |
| Junta | Les quatre targetes | Nivell 2 · Resum per a la Junta (5.2 i 5.4) | «La Junta decideix amb una pàgina» · matí 15 de 19, tarda 18 de 19, i el grau nou de 40 places també hi cap |
| Assistent | Pregunta escrita i «Comprova-ho» obert | Nivell 3 · Intel·ligència artificial | «Pregunta amb les teves paraules» · respon només amb dades de l'horari, i a «Comprova-ho» hi ha la consulta i les aules que ha trobat |
| Tancament | Fosa de 0,4 s a «Com estem avui» i fosa a negre | — | «Espais de l'Escola · Equip Neo» |

## Les ordres de la terminal

Al vídeo es veu una finestra de terminal pintada dins la gravació. Les ordres, però, s'executen de debò en aquell moment i la sortida que s'hi veu és la real. Les del verificador s'executen des de `repte/repte-horaris-escola`:

```bash
python -m horaris check paquet/proposta_partida.csv --semestre 2
```

```bash
python -m horaris check ../../resultats/nivell2/5.2/proposta.csv --semestre 2 --relaxacions ../../resultats/nivell2/5.2/relaxacions.csv
```


Quan la sortida és més llarga que la pantalla, el terminal puja suaument fins a l'ordre perquè es llegeixi el veredicte.

## Com es grava

Cal tenir l'app engegada al port 8511 (configuració «demo» de `.claude/launch.json`). Des de l'arrel del worktree:

```bash
python docs/demo/eines/grava_demo90.py
```

- [`eines/grava.py`](eines/grava.py): grava amb Chromium sense finestra (CDP `Page.startScreencast`). Pinta el cursor, els rètols, l'etiqueta de la part i el terminal dins la pàgina, i munta el vídeo a 30 fps constants.
- [`eines/grava_demo90.py`](eines/grava_demo90.py): el recorregut, amb els rètols i les ordres.
- **Esperes:** les de la IA i de les càrregues de pàgina es veuen, però al muntatge duren menys: com a molt 0,9 s per a la IA i 0,5 s per a una pàgina.
- **Control de l'assistent:** la gravació només es dona per bona si el nombre d'aules de la resposta és el mateix que el d'aules que llista «Comprova-ho», i la resposta no diu «No ho puc». Si no, es torna a gravar, fins a 4 vegades.

Durada final: 82,1 s.

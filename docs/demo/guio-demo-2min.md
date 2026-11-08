# Vídeo demo de 2 minuts

Vídeo de 2 minuts de la carpeta `demo/` de l'entrega: [`demo-2min.mp4`](demo-2min.mp4). És la versió llarga del [vídeo de 90 s](guio-demo-90s.md). Té el mateix estil, però sense la terminal del verificador, i deixa més temps per llegir cada rètol. Els segons exactes de cada rètol són a [`retols-demo-2min.json`](retols-demo-2min.json).

- **Un sol pla continu de l'app de debò,** amb el codi de `main` arrencat just abans de gravar.
- **Sense veu en off.** A dalt a la dreta, una etiqueta diu quina part del repte s'està resolent. A baix, un rètol diu què es veu i què hi tenim en compte.
- **Format:** 1920×1080, 30 fps, H.264, sense so.

## Recorregut

| Tram | Pantalla | Part del repte | Rètol (què es veu · què hi tenim en compte) |
|---|---|---|---|
| Portada | Com estem avui | Nivell 1 · Anàlisi | «1r i 2n al matí: sí, hi cabem» · 15 de 19 aules a l'hora més plena, i en guardem 2 de reserva. «Avui → amb la proposta» · 2.008 fora de torn → 459 excepcions declarades; 4.541 sense aula → 0 |
| Grau nou | Targeta «Hi cap un grau nou de 40 places?» | Nivell 2 · 5.4 Grau nou | «Hi cap un grau nou de 40 places: sí» · 235 classes noves sense moure cap classe de la resta |
| Problemes d'avui | Targeta «Quins altres problemes té l'horari d'avui?» | Nivell 1 · Anàlisi | «Avui l'horari té 7 tipus de problemes» · els més freqüents |
| Detall | «Mira el detall de les aules →» | Nivell 1 · Com ho sabem | «Cada xifra explica com s'ha calculat» |
| Horari proposat | 4t curs, «Mira l'exemple», «Canvia», detall d'una classe | Nivell 2 · 5.2 Torns nous | «1r i 2n al matí; 3r i 4t a la tarda». «Cada classe diu on era abans» |
| Imprevistos | Resum i «Mira l'exemple» | Nivell 2 · 5.3 Imprevistos | «Quatre imprevistos alhora, pocs canvis». «Aula avariada un dia: 6 classes canvien d'aula» |
| Junta | Les quatre targetes | Nivell 2 · Resum per a la Junta | «La Junta decideix amb una pàgina» |
| Assistent | Pregunta i «Comprova-ho» obert | Nivell 3 · Intel·ligència artificial | «Pregunta amb les teves paraules» · 6 aules lliures, i «Comprova-ho» les llista |
| Tancament | Torna a «Com estem avui» i fosa a negre | — | «Espais de l'Escola · Equip Neo» |

## Com es grava

Amb l'app engegada al port 8511 (configuració «demo» de `.claude/launch.json`), des de l'arrel del worktree:

```bash
python docs/demo/eines/grava_demo2min.py
```

[`eines/grava_demo2min.py`](eines/grava_demo2min.py) és el mateix gravador que el de 90 s. Les pauses es multipliquen per `LENT` (per defecte 2,08) perquè el vídeo duri uns 2 minuts. Les esperes de la IA i de les càrregues de pàgina es veuen, però al muntatge duren menys.

# Especificació de la part 2 · Proposta d'horari

> **Estat.** Afinada amb l'equip (entrevista del ds 7-11). No es programa ni es publica res fins que l'equip doni l'OK.
> La graella fa servir el disseny confirmat del nivell 1: B1, semàfor amb la resposta en gran (`docs/disseny/opcio-b1-resposta-gran.html`).

## La pregunta i la persona

La part 2 és el cor del repte i val el 50 % de la nota. Treballem el 2n semestre. La pregunta és: com faríem possible l'horari amb les línies mestres noves, i què costa?

Pensem en l'estudiant. Un bon horari és **rutinari**: cada setmana el mateix dia, la mateixa hora i la mateixa aula. També s'hi assembla al d'avui tant com es pugui, i qui va de tardes continua anant de tardes, tret que la regla 1 obligui a canviar-ho.

## Què lliurem

Cada pregunta es lliura amb:

- la proposta: un CSV `id_sessio,dia,h_ini,aula`, una fila per sessió;
- la sortida del verificador: `--json informe.json --violacions violacions.csv` (i `--relaxacions relaxacions.csv` si n'hi ha);
- la taula de xifres abans i després (vegeu «Com sabem que està fet»);
- una mini demo d'un minut.

Les preguntes són aquestes:

1. **5.1 Aules (5 %).** Amb l'horari d'avui, sense moure cap dia ni cap hora, donem aula a les 4.541 sessions que no en tenen. Es comprova amb `--nomes-aules`. Primer ha de ser VALIDA amb `--nomes-aules`: també es corregeixen les 43 sessions amb més alumnes que places i les 54 de tipus d'aula equivocat. Després es premia que sigui bona: aula base per grup, pocs canvis d'aula entre classes seguides i pocs canvis respecte de l'aula d'avui.
2. **5.2 Torns nous (25 %).** Cada sessió va al torn que li toca segons la regla 1, i diem què costa. Hi afegim el resum de la Junta.
3. **5.3 Imprevist (10 %).** Partim del 5.2 i resolem quatre imprevistos alhora, canviant el mínim.
4. **5.4 Grau nou de 40 places (10 %).** Col·loquem les 235 sessions del 2n semestre sobre el 5.2.

I, un sol cop, la graella setmanal per aula de la proposta més avançada.

## Regles que ens posem (a més del verificador)

Les regles són per ordre de prioritat. Quan dues xoquen, guanya la primera.

1. **Les regles del verificador.** Cap relaxació en silenci: totes es declaren amb el motiu.
2. **La rutina és una prioritat forta, no una regla dura** (decisió del ds 16:25). Planifiquem per activitat (`activitat_id`), no per sessió. Primer intentem que totes les sessions d'una activitat vagin al mateix dia, la mateixa hora i la mateixa aula totes les setmanes. Si el calendari (festius, aturades, avaluació) o una setmana concreta ho impedeixen, s'hi admeten excepcions puntuals: cada una es compta a la taula de xifres i s'explica. La rutina mai no passa per davant del verificador.
3. **El torn de l'estudiant.** Al 5.1, al 5.3 i al 5.4 cap sessió no canvia de torn. Al 5.2 una sessió només canvia de torn si la regla 1 l'hi obliga. Mai no es mou cap a l'altre torn una sessió que ja és al seu.
4. **Mínims canvis respecte d'avui.** Un canvi d'hora o de dia pesa més que un canvi d'aula. Quan una sessió s'ha de moure, primer es prova el mateix dia; només si no hi cap, o si hi guanya molt, va a un altre dia.
5. **Aula base i passadís.** La teoria i els problemes d'un grup, a la mateixa aula o al mateix passadís (mateixa espina i planta).
6. **Poques hores mortes.** Les classes mogudes s'enganxen a les altres del grup aquell dia.

## 5.2: què es pot moure

- Es pot moure el dia, l'hora i l'aula de **qualsevol sessió movible**, no només de les que són fora de torn. Cada canvi té un cost, i el solver només mou una sessió que ja era bé si hi guanya prou (fer-hi cabre les altres, l'aula base, menys hores mortes).
- No es toquen les de GEI i GEET+GEST de 1r i 2n ni els PLAB. Una sessió no canvia ni de setmana ni de durada.
- Avui hi ha 2.008 sessions al torn equivocat (R1-TORN). Unes 246 movibles de 1r i 2n són a la tarda i passen al matí. El gruix, unes 1.770 de 3r, 4t, dobles i màsters, és al matí i passa a la tarda.
- **El torn no el triem nosaltres.** El fixa la regla 1 (línies mestres de la Direcció): 1r i 2n al matí (8.30-14.30); 3r, 4t, dobles i màsters a la tarda (14.30-21.00). El verificador ho comprova (R1-TORN). Nosaltres triem el dia, l'hora i l'aula dins del torn de cada sessió, canviant el mínim.
- **Hi cap a tots dos torns (comprovat el ds 16:40, balanç d'hores d'aula de l'aulari a la pitjor setmana, sense PLAB ni dobles):**
  - **Matí:** 397 h contra 570 h (19 aules × 6 h × 5 dies), el 70 %. És el torn ajustat.
  - **Tarda:** passa de 105 h (les que avui ja hi són) a 259 h, perquè hi arriben 1.526 sessions de 3r i 4t que avui són al matí (+154 h). Contra 570 h (19 aules × 6 h de 15 a 21 h × 5 dies) és el 45 %. Per mida d'aula no falla cap llindar.
  - Per tant, no esperem cap excepció a la regla 1. És una condició necessària: no prova que l'horari encaixi sense solapaments de docent i alumnat. Això ho diu el solver.

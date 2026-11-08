# Revisió del punt 5 (5.1–5.4): errors trobats

Feta el ds 7-11 a les 22:55 per 12 subagents de Codex (`gpt-6.1-sol`, esforç alt), només en mode de lectura. N'hi ha tres per pregunta: un compara amb l'enunciat (PDF), un revisa la lògica del codi i un recalcula els resultats pel seu compte. Aquí només hi ha errors, sense solucions. «Confirmat» vol dir que l'han trobat dos o més revisors o que l'he comprovat jo.

Estat (ds 23:16): tots els punts greus i mitjans d’aquesta llista s’han arreglat i unit a main; vegeu el diari. Estat de partida: les quatre propostes passen el verificador oficial (5.1 VALIDA; 5.2, 5.3 i 5.4 VALIDA AMB RELAXACIONS DECLARADES), la comprovació de persones dona CORRECTE i passen les 224 proves.

## Ja arreglat aquesta nit

- Els README apuntaven a carpetes de treball antigues: ara tenen rutes relatives i l'ordre oficial (`n2-lliurament-3`).
- Al 5.1 li faltava `xifres.csv`: ja el té.

## Greus (afecten el que lliurem o el que diem)

1. **5.4 · Alumnes del grau nou amb dues classes alhora.** Confirmat (dos revisors i comprovat a mà). Hi ha 12 classes de problemes (`PAUL/92`, 20 alumnes) que coincideixen amb la teoria `TE/91`, on van els 40 alumnes. Exemple: N00078 i N00466, dimarts de 8.30 a 10.30. El verificador oficial no ho detecta perquè compara els números de grup (91 i 92). Per això la portada diu «Hi cap» quan no és cert.
2. **Junta · No surten les excepcions de torn que demanem.** Confirmat (quatre revisors). El PDF (línia 253) demana «les excepcions a la regla 1 que demaneu, cadascuna amb el motiu». El resum mostra 0 excepcions, però el verificador en compta 459 de declarades, entre elles S04526. La causa és que `nivell2/junta.py:200` descarta les sessions que conserven el dia i l'hora.
3. **Verificador · Pot donar per bo un informe antic.** Confirmat (tres revisors). Si el verificador falla, `nivell2/base.py` torna a llegir l'`informe.json` anterior com si fos d'aquesta execució.
4. **5.4 · La referència del 5.2 s'ha perdut en tornar a verificar.** L'he trobat jo en revisar aquesta llista. `nivell2/verificacio.py` no passa la proposta del 5.2 com a referència per al 5.4, i l'`informe.json` que ha reescrit `empaqueta` ja no inclou els canvis respecte del 5.2.
5. **5.2 · No es minimitzen les hores mortes.** Confirmat (dos revisors). El PDF les demana (línies 153 i 243). Passen de 72.930 a 107.370 minuts i els desplaçaments d'aula de 544 a 1.446, i no ho expliquem enlloc.
6. **5.2 · La reserva de 2 aules es compta més estricta que el verificador.** Confirmat (dos revisors). `nivell2/franges.py` compta les classes que toquen cada hora, i el verificador compta les aules diferents. Pot dir «impossible» d'un horari que és vàlid. La relaxació de S04526 es justifica amb una impossibilitat feta amb aquest càlcul.
7. **5.4 · Es mouen les 235 sessions noves sense que calgui.** Confirmat (dos revisors). El model només busca que sigui vàlid, sense cap objectiu de qualitat. Deixant-les a la seva hora original també és vàlid, amb menys canvis i menys hores mortes. A més, l'app diu «sense moure cap classe».
8. **5.1 · La millora «14 → 9» aules extra barreja els dobles graus.** Confirmat (dos revisors). Sis de les 14 són classes de dobles que no necessiten aula. Si no les comptem, passa de 8 a 9, és a dir, empitjora una mica.

## Mitjanes

9. **5.3 · L'app diu 53 classes que canvien d'aula, però són 54.** Confirmat (dos revisors). La sessió S11527, la cancel·lada, el verificador no la compta.
10. **`xifres.csv` del 5.2, 5.3 i 5.4 incomplets.** Confirmat. Hi falta el que diu l'especificació: rutina, aules per grup i setmana i canvis de torn. Tampoc s'expliquen els empitjoraments (desplaçaments, aules extra, canvis fora del passadís).
11. **5.4 · La columna «abans» de les xifres no és el 5.2 real.** És el 5.2 amb les 235 sessions noves sense aula: diu 110.730 minuts d'hores mortes, quan al 5.2 real n'hi ha 107.370.
12. **27 relaxacions dels dobles que no calen.** Confirmat. Són conflictes que ja hi eren avui. Inflen el total a 486, quan el verificador en compta 459.
13. **Junta · El «pic» no és de sessions simultànies.** Confirmat. Compta les aules ocupades durant una hora: surt 19, però el pic de classes alhora és 18.
14. **5.2 · L'impacte per titulació només compta els canvis d'hora.** No hi surten 109 sessions que només canvien d'aula. Exemple: GEQ 1r surt amb un 0 %, però té un 34,6 % de canvis d'aula.
15. **Graella · Els dobles surten com a «Pendent d'assignar aula».** Afecta 401 sessions que en realitat van a la classe d'un altre grup, que ja té aula.
16. **5.1 · Hi ha canvis d'aula evitables.** Un revisor ha trobat una proposta igual de vàlida amb 368 canvis respecte d'avui, en lloc de 399. El solver i el selector fan servir criteris diferents, amb llindars fixos de 13 i 166.
17. **5.3 · Errors del codi de reparació, demostrats amb exemples inventats.** No passen al resultat que lliurem, però el codi permet aquests casos:
    - pot crear conflictes nous respecte del 5.2;
    - pot tornar una classe de teoria al laboratori original, o deixar-la en una aula petita si el grup creix;
    - no té en compte les hores mortes ni la rutina;
    - amb la mateixa llavor pot donar 54 o 59 canvis.
18. **Pàgina d'Imprevistos:**
    - mostra «Comprovat» llegint `resum.json` sense comprovar el CSV;
    - espera el text «INVALIDA», però el verificador diu «NO VALIDA»;
    - diu «només movem les classes afectades», però també en mou dues de suport;
    - tradueix R2 i R4 amb noms equivocats.
19. **Si el solver no troba res, el 5.4 i el 5.2 esborren o barregen el lliurament vàlid anterior.**
20. **`comprova_persones` no mira el professorat**, només l'alumnat.
21. **Dubtes:**
    - No lliurem cap fitxer amb la graella setmanal per aula (PDF, línies 214–217). L'app la pot descarregar, però no és al paquet.
    - Al 5.3, el 10/03 de 14.30 a 15.30 només queda una aula de reserva útil, perquè l'aula avariada es compta com a lliure.
    - `relaxacions.csv` del 5.3 remet a un `diagnostic.md` que és a la carpeta del 5.2.
    - L'especificació diu 12 sessions a l'aula reservada (és l'horari d'avui); al 5.2 final en són 15.

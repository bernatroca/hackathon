# Revisió com a jurat i mentor (ds 16:05)

Feta per un subagent de Codex (gpt-6.1-sol, esforç alt, només lectura). Ha llegit l'enunciat, la part 1 (codi, xifres i app) i `.plans/nivell2-horari-spec.md`. El fil complet és `jurat-mentor-1` a `codex_status`.

## A. Nivell 1 com a jurat: 7/10

Té bona cobertura, xifres que es poden comprovar i una presentació pensada per al coordinador. La resposta central, però, és massa afirmativa.

Errors o matisos a corregir:

1. **«Sí, però just» sobreafirma.** El pic de 15 és amb les hores d'avui, i no inclou les classes de 1r i 2n que avui són a la tarda. El balanç d'hores sí que les inclou (389 de 570 h, 68 %). Text defensable: «Hi ha marge d'hores; encara no tenim un horari validat».
2. **74 % sense aula enganya com a feina pendent.** Les 5.722 sessions inclouen 919 PLAB, que no es toquen, i 262 dobles, que no necessiten aula. Les que cal assignar de debò són **4.541**. Cal posar a la targeta 5.722 = 4.541 + 919 + 262.
3. **Grau nou en verd és prematur.** Les xifres són d'una setmana, no del semestre. La consulta oblida 4 h amb alumnes = 0 (serien 181 h, no 185) i fa servir el màxim d'alumnes de les sessions compartides, mentre que el verificador els suma.
4. **El filtre de 1r i 2n deixa fora 156 sessions fixades `GEI:?`** amb `torn_requerit = mati` (312 h al semestre).
5. **L'oferta és nominal.** No descompta festius ni aturades. A més, la setmana amb el pic més alt no ha de ser per força la pitjor per a cada mida d'aula.
6. **«8 tipus de problemes»** barreja coses heretades i coses que es poden corregir. És millor posar a la portada **43 incidències d'aforament** (més 58 d'heretades) i deixar el catàleg per al detall.
7. **«6 docents tindrien»** → «podrien quedar amb matí i tarda si es mantenen els dies actuals».
8. **«Totes les respostes»** surt en 11 columnes. Ha de ser una graella de 2 o 3.

Preguntes que faria el jurat en directe:

1. Si porteu al matí totes les classes que hi han d'anar, quin pic surt? L'app no ho respon.
2. Quina setmana i quina mida d'aula són el coll d'ampolla, després de treure el calendari i la reserva? L'app no ho respon del tot.
3. De les 5.722 sense aula, quantes heu d'assignar de debò? Són 4.541, però la portada no ho diu.

Millores ordenades per impacte i esforç:

1. Corregir els veredictes de «hi cap» i del grau nou.
2. Desglossar el 5.722.
3. Unificar el balanç de capacitat: mateix conjunt de sessions, matrícula zero inclosa, compartides sumades i calendari descomptat.
4. Mostrar el matí i la tarda, i el coll d'ampolla per mida.
5. Fer la graella de «Totes les respostes» de 2 o 3 columnes.

## B. Part 2 com a mentor

- **El risc més gran: desdoblar de manera obligatòria els PAUL i SEM de més de 34 alumnes.** Obliga a declarar relaxacions, i VALIDA sense relaxacions passa per davant. A més, la segona meitat del grup no surt al CSV oficial, i un PAUL de 69 alumnes o més tampoc hi cap en dues meitats. Recomanació: deixar els desdoblaments i les fusions com a alternatives per a la Junta, només quan ja tinguem els quatre lliuraments.
- **5.1:** primer una proposta VALIDA amb `--nomes-aules`, que corregeixi també les 43 d'aforament i les 54 de tipus. No cal que l'aula sigui la mateixa totes les setmanes si això impedeix trobar una assignació vàlida.
- **5.3:** les sessions afectades s'han de calcular sobre el 5.2 que lliurem, no sobre l'horari d'avui. Si cal, es permet moure'n més, de mica en mica.
- **5.4:** cal distingir quatre respostes:
  - «hi cap»;
  - «no hi cap sense tocar el 5.2»;
  - «no l'hem trobat»;
  - «hem demostrat que no existeix».

  Un INFEASIBLE fet amb rutina obligatòria o amb el 5.2 congelat no demostra que no hi càpiga de cap manera.
- **Com triar la millor proposta:**
  1. VALIDA.
  2. Si cal relaxar, menys `incompliments_declarats`.
  3. Després, els objectius.

  El codi de sortida 0 no distingeix VALIDA de VALIDA AMB RELAXACIONS: cal mirar el JSON.
- **Riscos tècnics:**
  - **R8:** el verificador compta aules diferents dins de franges d'una hora, no classes simultànies cada 30 minuts.
  - **Calendari:** els candidats s'han de generar per data real.
  - **Compartides:** són una sola unitat, amb els alumnes sumats.
  - **Sense espai:** les sessions `sense_espai` continuen comptant per al torn, el docent i l'alumnat.
  - **R4-PLAB:** els PLAB són obstacles fixos per a la TE i el PAUL de la mateixa assignatura.
- **Ordre de feina:**
  1. Contracte i lector del verificador.
  2. 5.1 VALIDA.
  3. 5.2 VALIDA, i després optimitzar amb temps limitat.
  4. Congelar el 5.2; llavors el 5.3 i el 5.4 poden anar en paral·lel.
  5. La graella, el resum per a la Junta i reexecutar-ho tot.

  El frontend pot començar la graella amb dades de mostra.

## C. Decisions a prendre ara

1. **Hora d'entrega:** el diari diu les 12:00 de diumenge (correu de l'organització). Planificar per a les 12:00.
2. **Rutina contra validesa:** la rutina és prioritària, però amb excepcions mesurades. No pot passar mai per davant de la validesa.
3. **Desdoblaments i fusions:** com a alternatives posteriors, no com a part de la proposta principal.

El prompt complet que proposa per a la part 2 és al fil `jurat-mentor-1`. Es pot recuperar amb `codex_status`.

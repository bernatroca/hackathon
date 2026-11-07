# Revisió de disseny 1 (ds, vespre)

Subagent de Codex en mode només lectura. Ha revisat l'app amb quatre guies: les Web Interface Guidelines de Vercel, `better-ui`, `dataviz` i la maqueta B1. El fil complet és `revisio-disseny-1`, a `codex_status`. Abans d'aplicar res, l'app està desada a l'etiqueta `part1-v1`.

## Retocs petits (de 1 a 5 línies cadascun)

1. Plànol: el text blanc sobre blau només a partir del 72 % d'ocupació, i a sota en negre. Ara al 65-70 % té un contrast de 3,96:1.
2. Enllaços i botons «Com ho sabem →» en `#256abf`. Ara són `#2a78d6`, amb un contrast de 4,42:1 sobre blanc.
3. Mentre calcula: `opacity:.6` en lloc d'amagar el contingut.
4. «Per a tècnics» passa a dir «Detalls informàtics: consulta SQL i identificadors».
5. Quan un gràfic talla a 8 files, cal dir-ho.
6. El bloc gran només s'apila per sota de 760 px d'ample útil (ara, 1.100 px).
7. Paràgrafs de les targetes a 17 px, amb interlineat 1,5 i color `#52514e`.
8. Rajoles del plànol: contorn amb `:focus-visible`, i el canvi en passar el ratolí només als dispositius que en tenen.
9. En mòbil, «Proposem» sense alçada mínima.
10. Textos de «Proposem» que no prometin coses que encara diuen «aviat».

## Canvis grans (cal l'OK de l'equip)

- Bloc gran: si alguna mida d'aula no hi cap, ha de sortir en vermell, «Falten aules d'algunes mides». Ara posaria «Hi ha marge» encara que fallés.
- Semestre i setmana visibles sota el títol, no amagats a «Opcions».
- Enllaç «Veure les dades» (taula) a cada gràfic, i barres d'un gruix màxim de 24 px.
- Un sol títol principal per pàgina, i una adreça pròpia per a cada resposta (per compartir-la o tornar-hi).
- Icones SVG com les de la B1 (ara són els caràcters ✕ ! ✓) i missatges d'error planers.

## Paleta (contrast WCAG)

- Passen: la tinta (19,7:1), la tinta secundària (7,9:1) i els tres textos d'estat sobre el seu fons (verd 6,0, groc 5,4 i vermell 6,2).
- Fallen com a text normal: el blau `#2a78d6` (4,42:1 sobre blanc, 3,98:1 sobre el fons de la pàgina), i el text blanc del plànol entre el 65 % i el 72 %.

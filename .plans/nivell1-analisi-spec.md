# Part 1 · Anàlisi: com s'usen avui els espais de l'Escola, i hi cap el model nou?

Nivell 1 del repte d'horaris i espais 2027-28 (25 % de la nota). Les parts 2 (solver) i 3 (assistent) vindran després, en aquest ordre, i s'afegiran a la mateixa app.

## Persona

El tècnic de Gestió Acadèmica que avui fa els horaris en bona part a mà. Necessita saber, amb xifres que pugui defensar davant la Direcció, on van plens els espais i si les línies mestres noves (1r i 2n al matí, la resta a la tarda) hi caben.

## Què lliurem

- Una **app Streamlit** local, en català, que obre amb les **5 troballes més importants**. Cada troballa té:
  - una xifra gran;
  - una frase que la resumeix;
  - un gràfic;
  - **com s'ha calculat**: una o dues frases planeres que diuen què es compta i què s'exclou, i un desplegable amb la consulta SQL exacta i uns quants `id_sessio` d'exemple per buscar-los al CSV.
- Darrere la portada, pestanyes: mapa de calor, «Hi cap el matí?» i la resta de preguntes.
- Les 5 troballes de la portada les tria l'equip quan vegi tots els resultats. Fins llavors, la portada mostra les que diu `PORTADA` a `nivell1/troballes.py`.
- Funciona **només en local**: les dades no es publiquen. No es desplega a Cloudflare.

## Dades i definicions comunes

- Carpeta de dades: variable d'entorn `REPTE_DIR`. Si no hi és, `/Users/bernatroca/Bernat/Hackathon/repte/repte-horaris-escola`. Es llegeixen `paquet/sessions.csv`, `paquet/aules.csv`, `paquet/calendari.csv` i `paquet/escenaris/grau-nou-40/sessions_extra.csv`. No es modifiquen ni es copien al repositori.
- Motor: **DuckDB** amb SQL. Cada xifra surt d'una consulta `.sql` que l'app mostra tal qual.
- **Semestre per data**, no pel camp `semestre`: de setembre a gener és el 1r, i de febrer a juliol el 2n.
- **Blocs de 30 minuts**, de 8.30 a 21.00 (25 blocs). Una sessió ocupa els blocs que se solapen amb `[h_ini, h_fi)`. El matí va de 8.30 a 14.30 (12 blocs) i la tarda de 14.30 a 21.00.
- **Setmana**: la setmana ISO (`setmana`). Hi ha dues setmanes de referència:
  - *Típica*: la setmana amb el nombre de sessions igual a la mediana del semestre. Es fa servir per al mapa de calor, i n'hi ha un selector per veure qualsevol setmana.
  - *Pitjor*: la setmana amb el pic més alt. Es fa servir per a «hi cap»: si hi cap a la pitjor, hi cap sempre.
- **Demanda d'aulari**: sessions que necessiten aula de l'aulari. Se n'exclouen:
  - els PLAB, que van a espais de departament i no es toquen;
  - les sessions amb `sense_espai = 1`, les de doble titulació, que no necessiten espai propi.
- **Sessió compartida** (`id_compartida` no buit): compta una sola vegada.
- **Aules ordinàries**: tipus `Aules docents` (21). Se'n reserven 2 per franja (regla 8), i en queden **19** disponibles. Com a variant, s'hi poden sumar els 8 `Seminaris`, que també serveixen per a TE, PAUL i SEM.
- **Cohort**: cada valor de `titulacions_curs` (p. ex. `GED:1r`). Una sessió pot tenir-ne més d'una.

## Preguntes

Totes dues setmanes i tots dos semestres, amb selector de semestre. Les troballes sobre el model nou es calculen sobre el 2n semestre, que és el que avalua la part 2.

### De l'enunciat

1. **Ocupació per aula, dia i bloc**, per semestre. Mapa de calor `aula × (dia, bloc)` de la setmana triada, amb les sessions sense aula com a fila pròpia. Taula d'aules ordenada per % d'ocupació: quines van plenes i quines buides.
2. **Hores-aula necessàries i disponibles per franja.** Al 2n semestre, 5.722 de les 7.739 sessions (74 %) no tenen aula. Per a cada bloc: demanda d'aulari contra aules disponibles.
3. **Sessions fora del torn del model nou**, per titulació i curs. Fora de torn vol dir `torn_requerit = mati` amb inici a les 14.30 o més tard, o `tarda` amb inici abans de les 14.30. Sessions i hores-aula.
4. **Hi cap el matí?** És la xifra central i té tres capes:
   - a. **Pic d'avui**: classes de 1r i 2n del 2n semestre (sense PLAB ni dobles) alhora per bloc, amb les hores d'avui, contra 19 aules.
   - b. **Ocupació**: hores-aula de matí que demanen 1r i 2n, contra les que ofereixen les 19 aules.
   - c. **Per mida**: les sessions de 1r i 2n que avui són a la tarda no tenen hora de matí, així que es compta en hores-aula. Per a cada llindar de places `k` (les capacitats diferents de les aules: 24, 48, 50, 63, 88, 90, 100, 117, 130, 160), es compara:
     - **demanda**: hores de matí de sessions de 1r i 2n amb més de `k` alumnes;
     - **oferta**: hores de matí d'aules disponibles amb més de `k` places.

     Si a algun llindar la demanda supera l'oferta, és impossible, i aquest resultat serveix també de prova per al 5.4. Es mostra a la pitjor setmana i, com a variant, amb els seminaris.
5. **Grups amb més alumnes que places** a l'aula on són avui.

### Afegides per l'equip

6. **Seients buits**: `alumnes / capacitat` de cada sessió amb aula. Quines aules s'omplen menys del 50 % de mitjana, i quantes hores-aula grans es fan servir per a grups petits.
7. **Hores mortes d'avui**: buits entre dues classes del mateix grup d'alumnes, el mateix dia. El grup d'alumnes es defineix com al verificador: mateixa cohort, i la TE d'una línia amb els seus subgrups. Es dona per cohort i en total. És la línia base de l'objectiu 9 per a la part 2.
8. **Canvis d'aula per grup**: quantes aules diferents fa servir cada grup a la setmana, i quants canvis entre classes seguides surten del passadís. El passadís és l'espina i la planta: `Q4/0xxx` és la planta baixa i `Q4/1xxx` la primera.
9. **Dobles amb grup de matí**: sessions de doble titulació que avui fan classe amb un grup de 1r o 2n al matí, i que la regla vol a la tarda. Són 248 dels 2.008 R1-TORN del 2n semestre. Quantes són, de quines cohorts, i quantes hores-aula costaria separar-les.
10. **Docents a cavall**: docents que fan classe a 1r o 2n i també a 3r o 4t. Quants passarien a tenir matí i tarda el mateix dia amb el model nou, segons els dies en què fan classe avui.
11. **Marge per al grau nou**: hores-aula de matí que queden lliures, després de 4c, per a les 235 sessions del 2n semestre del grau nou de 40 places (`escenaris/grau-nou-40`). Indica si hi cap per mida.

«Pla contra realitat» queda fora, perquè el fitxer `validacio/geres-…csv` no és al paquet.

## Comprovació: les xifres han de quadrar amb l'enunciat

L'ordre `python -m nivell1.comprova` calcula totes les troballes, les imprimeix amb el seu `id` i comprova les xifres que dona l'enunciat. Si alguna no quadra, surt amb codi 1 i diu quina. Si una diferència és de definició, s'explica a la frase del mètode i s'ajusta l'esperat amb un comentari.

| Xifra | Esperat |
| --- | --- |
| Sessions totals / 2n semestre | 17.026 / 7.739 |
| Sessions del 2n semestre sense aula | 5.722 (74 %), de les quals 262 dobles i 919 PLAB |
| Pic de 1r i 2n al matí, hores d'avui (4a) | 15 classes alhora |
| Ocupació del matí de 1r i 2n (4b) | entre el 67 % i el 70 % de les 19 aules |
| Fora de torn al 2n semestre (3) | 2.008 (= R1-TORN del verificador) |
| Més alumnes que places al 2n semestre (5) | 43 (= R3-AFORAMENT) |
| Dobles amb grup de matí (9) | 248 |

## Repartiment: 5 subagents de Codex que no es trepitgen

Cada subagent treballa al seu worktree, a la seva branca, i només crea els seus fitxers. Cap fitxer és de dos subagents, així que les branques s'uneixen a `main` sense conflictes. L'esquelet comú el fa la integració (Claude) abans de llançar-los, i ningú més el toca: `nivell1/dades.py`, `nivell1/troballes.py`, `nivell1/comprova.py` i `requirements.txt`.

| Subagent | Worktree i branca | Preguntes (ID) | Fitxers que pot crear |
| --- | --- | --- | --- |
| dades-1 | `../hack-dades1` · `dades-1` | 1 `ocupacio`, 2 `hores-aula`, 5 `aforament` | `nivell1/preguntes/{ocupacio,hores_aula,aforament}.py`, `nivell1/consultes/{ocupacio,hores_aula,aforament}*.sql` |
| dades-2 | `../hack-dades2` · `dades-2` | 3 `fora-torn`, 4 `hi-cap-mati` | `nivell1/preguntes/{fora_torn,hi_cap_mati}.py`, `nivell1/consultes/{fora_torn,hi_cap_mati}*.sql` |
| dades-3 | `../hack-dades3` · `dades-3` | 7 `hores-mortes`, 9 `dobles-mati`, 11 `marge-grau-nou` | `nivell1/preguntes/{hores_mortes,dobles_mati,marge_grau_nou}.py`, `nivell1/consultes/{hores_mortes,dobles_mati,marge_grau_nou}*.sql` |
| dades-4 | `../hack-dades4` · `dades-4` | 6 `seients-buits`, 8 `canvis-aula`, 10 `docents-cavall` | `nivell1/preguntes/{seients_buits,canvis_aula,docents_cavall}.py`, `nivell1/consultes/{seients_buits,canvis_aula,docents_cavall}*.sql` |
| frontend | `../hack-frontend` · `frontend` | l'app | `app/**` |

- Si un subagent necessita una vista comuna nova, no toca `dades.py`: la fa dins la seva consulta (amb `WITH`) i la proposa a «problemes». La integració decideix si passa a l'esquelet.
- L'11 (`marge-grau-nou`) fa servir el resultat del 4c. Per no dependre de dades-2, recalcula l'oferta de matí amb la seva pròpia consulta i segueix la mateixa definició de l'especificació.
- Python per a tots: `/Users/bernatroca/Bernat/Hackathon/.venv/bin/python`. Té duckdb, pandas, streamlit, plotly i ortools, i no cal instal·lar res.

## Estructura i contracte entre rols

```text
nivell1/
  dades.py               ← esquelet: connexió DuckDB; taules sessions, grau_nou, aules, calendari, blocs; vista sessio_blocs
  troballes.py           ← esquelet: Troballa, registre automàtic, totes(), una(), PORTADA
  comprova.py            ← esquelet: python -m nivell1.comprova
  preguntes/<id>.py      ← subagents dades-1..4: ID, ORDRE, calcula(semestre, setmana), comprova()
  consultes/<id>*.sql    ← subagents dades-1..4: SQL amb paràmetres $semestre, $setmana
app/                     ← subagent FRONTEND
  app.py                 streamlit run app/app.py (st.navigation; pàgines de la part 1 ara, de la 2 i la 3 després)
  pagines/…
requirements.txt         ← integració (Claude): duckdb, pandas, streamlit, plotly
```

`nivell1/troballes.py` exposa:

```python
@dataclass
class Troballa:
    id: str                 # 'ocupacio', 'hi-cap-mati', … (1-11 de dalt)
    titol: str              # pregunta curta
    xifra: str              # «15 de 19», «74 %»…
    frase: str              # la troballa en una frase
    metode: str             # com s'ha calculat, en llenguatge planer
    sql: str                # la consulta exacta que s'ha executat
    taula: pandas.DataFrame # les dades del gràfic
    exemples: list[str]     # id_sessio per comprovar-ho al CSV
    grafic: str             # 'heatmap' | 'barres' | 'linia' | 'taula'

def totes(semestre: int = 2, setmana: str | None = None) -> list[Troballa]: ...
def una(id: str, semestre: int = 2, setmana: str | None = None) -> Troballa: ...
PORTADA: list[str]          # ids de les 5 troballes de la portada
```

El frontend pot començar amb una `Troballa` de mostra feta a mà fins que dades acabi. L'app no fa càlculs: només crida `totes()` i `una()`, amb `st.cache_data`.

## Interfície

- Català. Xifres amb format català (`5.722`, `74 %`).
- Portada: 5 targetes. Cada targeta té la xifra gran, el títol, la frase i un gràfic petit. En clicar-la, s'obre la troballa sencera.
- Selector de semestre i de setmana a la barra lateral. Per defecte, el 2n semestre i la setmana típica.
- Mapa de calor amb plotly: aules a les files, dia i bloc a les columnes, i color segons ocupació. La fila «sense aula» va a part.
- «Hi cap el matí?»: el pic per bloc contra la línia de 19, i el gràfic per mida (demanda contra oferta per llindar), on el llindar que falla surt marcat.

## Feta quan

1. `python -m nivell1.comprova` surt amb codi 0, i totes les xifres de la taula de comprovació quadren.
2. `streamlit run app/app.py` obre la portada amb 5 troballes, i cada troballa mostra la xifra, la frase, el gràfic, el mètode i el SQL.
3. **Mini demo**: un minut que forma part de la demo de 3 minuts, un per part. El vídeo i el guió es fan en una conversa a part amb l'eina de vídeo de Claude. El minut de la part 1 segueix aquest ordre:
   - la pregunta;
   - la portada amb les 5 troballes;
   - «Hi cap el matí?»;
   - el SQL obert;
   - un `id_sessio` buscat al CSV.

## Fora d'abast

- El solver (part 2) i l'assistent (part 3).
- Desplegar a Cloudflare.
- La validació amb el GERES.
- Exàmens.

## Prioritat

Tan ràpid com es pugui, per passar aviat a les parts 2 i 3. Si cal retallar, l'ordre és:

1. Es fan primer les preguntes 1 a 5, la comprovació i la portada.
2. Després les afegides, en l'ordre 7, 9, 11, 6, 8, 10.

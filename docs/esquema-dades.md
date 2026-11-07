# Esquema de les dades del repte (amb files inventades)

Aquest fitxer descriu els CSV per a qui escrigui codi sense veure les dades reals. **Totes les files d'exemple són inventades**: codis, noms, grups i docents no existeixen. Les dades reals són a `repte/repte-horaris-escola/paquet/` i no surten de l'ordinador.

## sessions.csv (17.026 files: una per classe datada)

| Columna | Tipus | Exemple / valors |
|---|---|---|
| id_sessio | text | `S95000` (clau de la proposta) |
| activitat_id | text | `A9500` (mateix grup, dia i hora cada setmana) |
| id_compartida | text, pot ser buit | `C95000` si és la mateixa classe física que una altra |
| codi | text (6 dígits) | `100000` |
| assignatura | text | nom de l'assignatura |
| tipus | `TE` · `PAUL` · `PLAB` · `SEM` | teoria, problemes, laboratori, seminari |
| grup | text | `TE/81`, `PAUL/811` |
| semestre | `C/1` · `C/2` · `A/0` | no és fiable: el semestre es treu de la data |
| data | data `AAAA-MM-DD` | `2027-02-15` |
| setmana | text ISO | `2027-W07` |
| dia | `L` `M` `X` `J` `V` | dia de la setmana |
| h_ini, h_fi | hora `HH:MM` | `08:30`, `10:30` |
| durada_min | enter | 60, 120 o 180 |
| alumnes | enter | 0 si no hi ha dada |
| capacitat_grup | enter, pot ser buit | places previstes |
| aula_partida | text, pot ser buit | `Q9/5015`; buit = sense aula |
| aules_addicionals_partida | text, pot ser buit | altres aules separades per `|` |
| plans | text | codis de pla separats per `|` |
| titulacions_curs | text | `GXX:1r` o `GXX:2n|GYY:2n` (titulació:curs) |
| dc | `P` · `S` · buit | docència compartida |
| torn_requerit | `mati` · `tarda` | torn que li toca amb el model nou |
| fixada | text, pot ser buit | `R1: GXX 1r` o `R7: PLAB` si no es pot moure |
| docents | text | pseudònims `D900|D901` |
| alumnes_origen | `sigma` · `estimat` · `sense_dada` | d'on surt `alumnes` |
| sense_espai | `0` · `1` | 1 = grup de doble titulació, sense aula pròpia |

```csv
id_sessio,activitat_id,id_compartida,codi,assignatura,tipus,grup,semestre,data,setmana,dia,h_ini,h_fi,durada_min,alumnes,capacitat_grup,aula_partida,aules_addicionals_partida,plans,titulacions_curs,dc,torn_requerit,fixada,docents,alumnes_origen,sense_espai
S90001,A9001,,100000,Assignatura Inventada I,TE,TE/81,C/2,2027-02-15,2027-W07,L,08:30,10:30,120,85,90,Q9/5016,,9999,GXX:1r,,mati,,D900,sigma,0
S90002,A9002,C90001,100001,Assignatura Inventada II,PAUL,PAUL/811,C/2,2027-02-16,2027-W07,M,15:00,17:00,120,42,,,,9999|9998,GXX:3r|GYY:3r,P,tarda,,D901|D902,estimat,0
```

## aules.csv (56 espais)

| Columna | Tipus | Exemple / valors |
|---|---|---|
| aula | text | `Q9/5021` (espina Q4, planta 0) |
| edifici | text | `Q4` |
| tipus | text | `Aules docents` (21), `Laboratoris docents` (25), `Seminaris` (8), `Aules informàtiques` (2) |
| descripcio | text | descripció de l'inventari |
| capacitat | enter | places |
| ordinaria | `0` · `1` | 1 = aula docent (compta per a la reserva de 2 aules) |

```csv
aula,edifici,tipus,descripcio,capacitat,ordinaria
Q9/0001,Q9,Aules docents,Aula inventada,90,1
Q9/0002,Q9,Laboratoris docents,Laboratori inventat,24,0
```

## activitats.csv (1.930 files: les sessions agrupades per grup, dia i hora)

Columnes: activitat_id, codi, grup, semestre, dia, h_ini, h_fi, assignatura, tipus, n_sessions (enter), setmana_primera, setmana_ultima, alumnes (enter), aules_partida (text, `|`), sessions_sense_aula (enter), titulacions_curs, torn_requerit, fixada, docents, sense_espai.

```csv
activitat_id,codi,grup,semestre,dia,h_ini,h_fi,assignatura,tipus,n_sessions,setmana_primera,setmana_ultima,alumnes,aules_partida,sessions_sense_aula,titulacions_curs,torn_requerit,fixada,docents,sense_espai
A9001,100000,TE/81,C/2,L,08:30,10:30,Assignatura Inventada I,TE,14,2027-W06,2027-W22,85,Q9/5016,0,GXX:1r,mati,,D900,0
```

## calendari.csv (32 files: dies sense classe o amb aturades)

Columnes: data (data), tipus (`festiu` · `no_lectiu` · `aturada` · `avaluacio`), h_ini i h_fi (hora, buides si és tot el dia), motiu (text), font (text).

```csv
data,tipus,h_ini,h_fi,motiu,font
2027-04-01,festiu,,,Festiu inventat,calendari
```

## proposta_partida.csv (format de lliurament)

Columnes: id_sessio, dia (`L`…`V`), h_ini (`HH:MM`), aula (text, pot ser buit). A les sessions cancel·lades d'un escenari s'hi afegeix la columna `data`.

```csv
id_sessio,dia,h_ini,aula
S90001,L,08:30,Q9/5016
```

## Altres

- `plans.csv`: pla, titulacions, descripcio, fitxer_origen, data_extraccio.
- `escenaris/contingencies/escenari.json`: aules tancades (aula, data_ini, data_fi), canvis d'alumnes (codi, grup, alumnes) i sessions cancel·lades (id_sessio, recuperar_fins).
- `escenaris/grau-nou-40/sessions_extra.csv`: mateixes columnes que sessions.csv (sense `sense_espai`), 478 sessions d'un grau nou.

## Què volem veure a l'app

Ja la tenim feta (`app/app.py`, disseny B1 a `docs/disseny/`). Per a un coordinador, no per a un tècnic:

1. **Hi cap el matí?** Resposta en gran, 19 quadrets (un per aula disponible) i barres per dia amb el número escrit.
2. **Targetes de semàfor**: classes al torn equivocat, classes sense aula, grau nou, aforament i altres problemes. Cada una amb la xifra, què vol dir i «Proposem».
3. **Plànol d'aules** per espina i planta, més fosques com més ocupades.
4. **Horari d'un grup** i **graella per aula** (part 2).
5. Res de mapes de calor, eixos tècnics ni SQL a primera vista.

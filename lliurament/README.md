# Lliurament · Espais de l'Escola (UAB THE HACK! 2026)

Què entreguem per a cada nivell del repte i on és. Tot es pot comprovar amb el verificador oficial i amb les dades del paquet.

| Nivell | Què demana l'enunciat | On és |
| --- | --- | --- |
| 1 · Anàlisi | Quadre de comandament i les cinc troballes, cada una amb la xifra i com s'ha calculat | L'app (`streamlit run app/app.py`): «Com estem avui» i «Totes les respostes». Cada detall diu com s'ha calculat. `python -m nivell1.comprova` comprova totes les xifres. |
| 2 · Quatre preguntes | Per a cada pregunta, la proposta i la sortida del verificador; la graella setmanal per aula, un sol cop | `lliurament-nivell2.zip` (descomprimit a l'arrel crea [`resultats/nivell2/`](../resultats/nivell2/)): `5.1`–`5.4` amb `proposta.csv`, `informe.json`, `violacions.csv`, `relaxacions.csv` (si n'hi ha), `xifres.csv` i `README.md` (ordres per generar-la i verificar-la). Graelles per aula a `graelles/`, dins el mateix ZIP. |
| 3 · IA | Una demo i una explicació de com es comprova el que diu | L'Assistent de l'app (botó de baix a la dreta) i [`com-es-comprova-l-assistent.md`](com-es-comprova-l-assistent.md). |
| Presentació | Diapositives i vídeo demo | Carpetes `presentacio/` (.pptx i PDF) i `demo/` (vídeo) del .zip de l'entrega. |

## Veredictes del verificador oficial

| Pregunta | Veredicte |
| --- | --- |
| 5.1 Aules amb l'horari d'avui | VALIDA |
| 5.2 Torns nous | VALIDA AMB RELAXACIONS DECLARADES |
| 5.3 Imprevistos | VALIDA AMB RELAXACIONS DECLARADES |
| 5.4 Grau nou de 40 places | VALIDA AMB RELAXACIONS DECLARADES |

## Com ho comprova el jurat des de la terminal

Amb el paquet oficial a `repte/repte-horaris-escola/` (o `REPTE_DIR` apuntant-hi), des de l'arrel del repositori:

```bash
export REPTE_DIR="$PWD/repte/repte-horaris-escola"
REPOSITORI="$PWD"; cd "$REPTE_DIR"
# 5.1 (només aules)
python -m horaris check "$REPOSITORI/resultats/nivell2/5.1/proposta.csv" --semestre 2 --nomes-aules
# 5.2
python -m horaris check "$REPOSITORI/resultats/nivell2/5.2/proposta.csv" --semestre 2 --relaxacions "$REPOSITORI/resultats/nivell2/5.2/relaxacions.csv"
# 5.3 (escenari d'imprevistos, referència 5.2)
python -m horaris check "$REPOSITORI/resultats/nivell2/5.3/proposta.csv" --semestre 2 --escenari paquet/escenaris/contingencies --referencia "$REPOSITORI/resultats/nivell2/5.2/proposta.csv" --relaxacions "$REPOSITORI/resultats/nivell2/5.3/relaxacions.csv"
# 5.4 (escenari del grau nou, referència 5.2)
python -m horaris check "$REPOSITORI/resultats/nivell2/5.4/proposta.csv" --semestre 2 --escenari paquet/escenaris/grau-nou-40 --referencia "$REPOSITORI/resultats/nivell2/5.2/proposta.csv" --relaxacions "$REPOSITORI/resultats/nivell2/5.4/relaxacions.csv"
cd "$REPOSITORI"
```

Per revalidar-ho tot de cop i tornar a crear el ZIP: `python -m nivell2.empaqueta --sortida lliurament-zip`. Les preguntes preparades per a la terminal (verificador i assistent) són al [README principal](../README.md#preguntes-des-de-la-terminal).

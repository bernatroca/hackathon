# Com validar la part 1 des d'un altre ordinador

Calen uns 10 minuts. Les dades del repte **no són a GitHub** (no es poden publicar): cadascú les baixa del OneDrive del repte.

## 1. Baixa el codi

```bash
git clone https://github.com/bernatroca/hackathon.git
cd hackathon
```

(El repositori és privat: en Bernat t'hi ha de convidar abans.)

## 2. Posa les dades del repte

1. Baixa el zip de dades del OneDrive del repte: `REPTE ESCOLA/DADES/repte-horaris-escola-dades-i-verificador.zip`.
2. Descomprimeix-lo dins `hackathon/repte/`. Ha de quedar `hackathon/repte/repte-horaris-escola/paquet/sessions.csv`.
3. Digues a l'app on són:

```bash
export REPTE_DIR="$PWD/repte/repte-horaris-escola"
```

## 3. Instal·la i arrenca

Cal Python 3.11 o més nou.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m nivell1.comprova
```

L'última ordre ha d'acabar amb `29/29 comprovacions correctes`.

```bash
streamlit run app/app.py
```

S'obre el navegador a http://localhost:8501.

## 4. Valida

Segueix els passos de [VALIDATION.md](../VALIDATION.md), que és a l'arrel del repositori. Per a cada pas, apunta si surt el que diu després de la fletxa (→). Si no surt, fes una captura i escriu què has vist.

Les propostes 5.1–5.4 són a `resultats/nivell2/`. Amb les dades i els resultats disponibles:

```bash
python -m pytest app nivell2 -q -p no:cacheprovider
```

Resultat de referència: 747 correctes i 1 omesa (uns 90 segons).
El servidor de l’assistent tria un port local lliure i només accepta localhost.

Envia els comentaris a en Bernat.

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

Cal Python 3.10 o més nou.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m nivell1.comprova
```

L'última ordre ha d'acabar amb `18/18 comprovacions correctes`.

```bash
streamlit run app/app.py
```

S'obre el navegador a http://localhost:8501.

## 4. Valida

Segueix els passos de [VALIDATION.md](../VALIDATION.md), que és a l'arrel del repositori. Per a cada pas, apunta si surt el que diu després de la fletxa (→). Si no surt, fes una captura i escriu què has vist.

Quatre passos encara surten malament i és normal, perquè són correccions pendents:

- la resposta gran encara diu «Sí, però just»;
- la targeta de les classes sense aula no mostra les 4.541 que cal assignar;
- el grau nou surt en verd;
- «Totes les respostes» surt en moltes columnes estretes.

Envia els comentaris a en Bernat.

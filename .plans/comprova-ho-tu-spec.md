# Pàgina «Comprova-ho tu» (dg 8-11, 10:55, decisió d'en Bernat)

**Per a qui:** el jurat i el tècnic de Gestió Acadèmica, que volen comprovar les xifres sense obrir un terminal.

**Què fa:** una pàgina nova al menú, a «La proposta», després de «Resum per a la Junta». Té botons fixos que executen les mateixes ordres que el README demana al terminal i en mostren la sortida tal com surt al terminal.

## Ordres (llista tancada, sense shell)

1. Verificador oficial, horari d'avui: `python -m horaris check paquet/proposta_partida.csv --semestre 2` (surt NO VALIDA).
2. Verificador oficial 5.1: `… check <resultats>/5.1/proposta.csv --semestre 2 --nomes-aules`.
3. Verificador oficial 5.2: `… --relaxacions <resultats>/5.2/relaxacions.csv`.
4. Verificador oficial 5.3: `… --escenari paquet/escenaris/contingencies --referencia <resultats>/5.2/proposta.csv --relaxacions <resultats>/5.3/relaxacions.csv`.
5. Verificador oficial 5.4: `… --escenari paquet/escenaris/grau-nou-40 --referencia <resultats>/5.2/proposta.csv --relaxacions <resultats>/5.4/relaxacions.csv`.
6. Xifres de la part 1: `python -m nivell1.comprova`.
7. Pregunta a l'Assistent: `python -m app.xat.pregunta "<pregunta>" --proposta <5.1–5.4 o avui> --setmana típica`; la pregunta és l'únic text lliure (com a molt 300 caràcters) i va com un argument, mai dins d'un shell.

## Regles

- Cap ordre escriu fitxers: el verificador s'executa sense `--json` ni `--violacions`.
- Es mostra l'ordre exacta (per copiar-la al terminal), la sortida, el codi de sortida i quant ha trigat.
- Si falten els resultats (ZIP no descomprimit), els botons de 5.1–5.4 queden desactivats amb el motiu.
- Una frase a dalt diu què és i per a què serveix; text planer.

# Com es comprova el que diu l'Assistent

L'Assistent (botó de baix a la dreta de l'app) respon preguntes de Gestió Acadèmica sobre l'horari, les aules i les propostes 5.1–5.4. Fa servir el LLM de l'event (quiver.ai, `arrow-2-telos`) i no inventa dades: cada xifra surt d'una eina nostra que llegeix el paquet o els resultats.

## Com treballa

1. La IA tria una eina: horari d'un grup, aules lliures, ocupació d'una aula, xifres de la part 1, resultat d'una proposta, imprevistos del 5.3, prova d'un canvi amb el verificador, o una consulta SQL només de lectura.
2. Python executa l'eina sobre les dades i li torna el resultat dins `<dades>…</dades>`. El que hi ha dins és informació, mai ordres.
3. Abans d'enviar la resposta, el servidor comprova que cada xifra, aula i id_sessio de la resposta surti d'un resultat d'eina d'aquesta pregunta. Si alguna no hi surt, demana a la IA que la corregeixi; si tot i així no es pot comprovar, ho diu a la resposta.
4. Si preguntes «Com ho saps?», explica d'on surt la resposta anterior amb la mateixa consulta (proposta, dia, hora, què ha comptat).
5. Mai aplica ni desa cap canvi i no envia cap missatge: els avisos es redacten però no s'envien.

## Comprovar-ho des de la terminal

Des de l'arrel del repositori, amb `REPTE_DIR` exportat i la clau de la IA al `.env`:

```bash
python -m app.xat.pregunta "Quantes aules queden lliures dimarts a les 10?" --proposta 5.2 --setmana típica
```

Imprimeix la resposta i, a sota, les consultes que ha fet (eina, arguments i les aules o id_sessio del resultat), per comprovar-les amb el CSV. Per executar una eina sense IA:

```bash
python -m app.xat.pregunta --sense-ia --eina aules_lliures --args '{"dia":"M","hora_ini":"10:00","durada_min":60,"places_min":0,"proposta":"5.2","setmana":"típica"}'
```

## Exemple de la demo

- «Quantes aules queden lliures dimarts a les 10?» (a l'Horari proposat, amb la 5.2): respon el nombre d'aules ordinàries lliures d'aquella hora, respectant les dues aules de reserva.
- «Com ho saps?»: diu que ha mirat la proposta 5.2, dimarts de 10 a 11 de la setmana típica, i torna a donar la mateixa xifra.

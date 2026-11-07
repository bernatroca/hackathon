-- Agenda d'alumnat: inclou laboratoris i dobles perquè també ocupen temps.
WITH base AS (
 SELECT *, unnest(string_split(titulacions_curs, '|')) AS cohort,
 split_part(grup, '/', -1) AS num_grup
 FROM sessions WHERE sem = $semestre AND ($setmana IS NULL OR setmana = $setmana)
), linies AS (
 SELECT *, CASE WHEN length(num_grup) >= 3 AND
 (tipus <> 'TE' OR ends_with(num_grup, '0'))
 THEN left(num_grup, length(num_grup)-1) ELSE num_grup END AS linia
 FROM base
)
SELECT id_sessio, unitat, cohort, data, tipus, num_grup, linia, ini_min, fi_min
FROM linies ORDER BY cohort, data, ini_min, id_sessio

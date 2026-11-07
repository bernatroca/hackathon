-- Una agenda per subgrup i dia, amb les teories compatibles.
WITH base AS (
 SELECT id_sessio, unitat, data, tipus, ini_min, fi_min,
 unnest(string_split(titulacions_curs, '|')) AS cohort,
 split_part(grup, '/', -1) AS num_grup
 FROM sessions WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana)
), linies AS (
 SELECT *, CASE WHEN length(num_grup)>=3 AND
 (tipus<>'TE' OR ends_with(num_grup, '0'))
 THEN left(num_grup, length(num_grup)-1) ELSE num_grup END AS linia
 FROM base
), subgrups AS (
 SELECT DISTINCT cohort, data, num_grup, linia FROM linies WHERE tipus<>'TE'
), agendes AS (
 SELECT s.cohort, s.data, 'S:' || s.num_grup AS agenda,
 l.id_sessio, l.unitat, l.ini_min, l.fi_min
 FROM subgrups s JOIN linies l ON s.cohort=l.cohort AND s.data=l.data
 AND ((l.tipus<>'TE' AND l.num_grup=s.num_grup)
 OR (l.tipus='TE' AND (l.linia=s.linia OR l.num_grup=s.num_grup)))
 UNION ALL
 SELECT l.cohort, l.data, 'T:' || l.linia AS agenda,
 l.id_sessio, l.unitat, l.ini_min, l.fi_min
 FROM linies l WHERE l.tipus='TE' AND NOT EXISTS (
 SELECT 1 FROM subgrups s WHERE s.cohort=l.cohort AND s.data=l.data
 AND (s.linia=l.linia OR s.num_grup IN (
 SELECT t.num_grup FROM linies t WHERE t.cohort=l.cohort AND t.data=l.data
 AND t.tipus='TE' AND t.linia=l.linia)))
), uniques AS (
 SELECT * FROM agendes QUALIFY row_number() OVER (
 PARTITION BY cohort,data,agenda,unitat ORDER BY ini_min,id_sessio)=1
), anteriors AS (
 -- Màxim acumulat, en comptes de LAG: uneix també intervals encavalcats.
 SELECT *, max(fi_min) OVER (PARTITION BY cohort,data,agenda
 ORDER BY ini_min,id_sessio ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fi_anterior
 FROM uniques
), buits AS (
 SELECT *, CASE WHEN ini_min>fi_anterior AND ((fi_anterior<=870)=(ini_min<870))
 THEN ini_min-fi_anterior ELSE 0 END AS minuts FROM anteriors
), totals AS (
 SELECT cohort, sum(minuts) AS minuts,
 list(id_sessio ORDER BY data,ini_min,id_sessio) FILTER (WHERE minuts>0) AS exemples
 FROM buits GROUP BY cohort
)
SELECT c.cohort, coalesce(t.minuts,0)::BIGINT AS minuts,
 coalesce(t.minuts,0)/60.0 AS hores, t.exemples
FROM (SELECT DISTINCT cohort FROM linies) c LEFT JOIN totals t USING(cohort)
ORDER BY cohort

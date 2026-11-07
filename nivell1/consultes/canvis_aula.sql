-- Agenda del verificador: cohort, línia i subgrup; la teoria s'afegeix a cada subgrup del dia.
WITH base AS (
 SELECT *, split_part(grup, '/', -1) AS num_grup,
 CASE WHEN tipus = 'TE' THEN
   CASE WHEN length(split_part(grup, '/', -1)) >= 3 AND ends_with(grup, '0')
        THEN left(split_part(grup, '/', -1), -1) ELSE split_part(grup, '/', -1) END
 ELSE CASE WHEN length(split_part(grup, '/', -1)) >= 3
        THEN left(split_part(grup, '/', -1), -1) ELSE split_part(grup, '/', -1) END END AS linia
 FROM sessions WHERE sem = $semestre AND ($setmana IS NULL OR setmana = $setmana)
), cohorts AS (
 SELECT b.*, c.cohort FROM base b, unnest(string_split(coalesce(titulacions_curs,''), '|')) c(cohort)
 WHERE c.cohort <> ''
), grups AS (
 SELECT cohort, linia, data, num_grup AS subgrup FROM cohorts WHERE tipus <> 'TE'
 UNION
 SELECT cohort, linia, data, '*' FROM cohorts c WHERE NOT EXISTS (
 SELECT 1 FROM cohorts p WHERE p.cohort=c.cohort AND p.linia=c.linia AND p.data=c.data AND p.tipus<>'TE')
), agenda AS (
 SELECT g.cohort, g.linia, g.subgrup, c.data, c.ini_min, c.fi_min, c.id_sessio, c.unitat, c.aula_partida
 FROM grups g JOIN cohorts c ON g.cohort=c.cohort AND g.linia=c.linia AND g.data=c.data
 AND (c.tipus='TE' OR c.num_grup=g.subgrup)
 QUALIFY row_number() OVER (PARTITION BY g.cohort,g.linia,g.subgrup,c.data,c.unitat ORDER BY c.id_sessio)=1
), passos AS (
 SELECT *, lag(aula_partida) OVER w AS anterior, lag(fi_min) OVER w AS fi_anterior
 FROM agenda WINDOW w AS (PARTITION BY cohort,linia,subgrup,data ORDER BY ini_min,id_sessio)
)
SELECT cohort, linia, subgrup, count(DISTINCT aula_partida) AS aules_diferents,
 count(*) FILTER (WHERE anterior IS NOT NULL AND aula_partida IS NOT NULL AND anterior<>aula_partida) AS canvis_aula,
 count(*) FILTER (WHERE anterior IS NOT NULL AND aula_partida IS NOT NULL
 AND split_part(anterior,'/',1)||'/'||left(split_part(anterior,'/',2),1)
 <> split_part(aula_partida,'/',1)||'/'||left(split_part(aula_partida,'/',2),1)) AS fora_passadis,
 count(*) FILTER (WHERE aula_partida IS NULL) AS sense_aula,
 count(*) FILTER (WHERE ini_min < fi_anterior) AS passos_solapats,
 list(DISTINCT id_sessio ORDER BY id_sessio) AS exemples
FROM passos GROUP BY cohort,linia,subgrup ORDER BY fora_passadis DESC,aules_diferents DESC,cohort,linia,subgrup

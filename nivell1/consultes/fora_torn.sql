-- R1-TORN compta sessions individuals; les hores-aula dedupliquen compartides.
WITH fora AS (
 SELECT * FROM sessions WHERE sem=$semestre
 AND torn_requerit IN ('mati','tarda') AND torn_requerit<>torn_actual
), detall AS (
 SELECT f.*, abast, cohort FROM fora f
 CROSS JOIN (VALUES ('semestre'),('setmana')) a(abast)
 CROSS JOIN LATERAL unnest(list_concat(['TOTAL'],string_split(titulacions_curs,'|'))) c(cohort)
 WHERE abast='semestre' OR setmana=$setmana
), unitats AS (
 SELECT abast,cohort,unitat,count(*) AS directes,
 count(*) FILTER(WHERE coalesce(fixada,'')='') AS sessions,
 count(*) FILTER(WHERE coalesce(fixada,'')<>'') AS heretades,
 max(CASE WHEN demanda_aulari THEN durada_min ELSE 0 END)/60.0 AS hores_directes,
 max(CASE WHEN demanda_aulari AND coalesce(fixada,'')='' THEN durada_min ELSE 0 END)/60.0 AS hores,
 min(id_sessio) AS exemple
 FROM detall GROUP BY abast,cohort,unitat
)
SELECT abast,cohort,sum(directes)::BIGINT AS sessions_directes,
 sum(sessions)::BIGINT AS sessions,sum(heretades)::BIGINT AS heretades,
 sum(hores_directes) AS hores_aula_directes,sum(hores) AS hores_aula,
 list(exemple ORDER BY exemple) AS exemples
FROM unitats GROUP BY abast,cohort ORDER BY abast,cohort;

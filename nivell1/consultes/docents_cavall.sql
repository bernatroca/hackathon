-- Els docents són assignats al grup: no sabem qui imparteix cada sessió.
WITH docencia AS (
 SELECT DISTINCT s.id_sessio,s.unitat,s.data,s.dia, trim(d.docent) AS docent,
 bool_or(split_part(c.cohort,':',2) IN ('1r','2n')) AS inicial,
 bool_or(split_part(c.cohort,':',2) IN ('3r','4t')) AS superior
 FROM sessions s,
 unnest(string_split(coalesce(s.docents,''),'|')) d(docent),
 unnest(string_split(coalesce(s.titulacions_curs,''),'|')) c(cohort)
 WHERE s.sem=$semestre AND ($setmana IS NULL OR s.setmana=$setmana) AND trim(d.docent)<>''
 GROUP BY s.id_sessio,s.unitat,s.data,s.dia,trim(d.docent)
), dies AS (
 SELECT docent,data,dia,bool_or(inicial) AS inicial,bool_or(superior) AS superior
 FROM docencia GROUP BY docent,data,dia
), resum AS (
 SELECT docent,bool_or(inicial) AND bool_or(superior) AS a_cavall,
 count(*) FILTER (WHERE inicial AND superior) AS dies_mati_tarda,
 string_agg(dia,', ' ORDER BY dia) FILTER (WHERE inicial AND superior) AS dies
 FROM dies GROUP BY docent
)
SELECT r.*, (SELECT list(DISTINCT id_sessio ORDER BY id_sessio) FROM docencia d
 WHERE d.docent=r.docent AND (d.inicial OR d.superior)) AS exemples
FROM resum r WHERE a_cavall ORDER BY dies_mati_tarda DESC,docent

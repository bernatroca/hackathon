-- Els docents són assignats al grup: no sabem qui imparteix cada sessió.
WITH docencia AS (
 SELECT DISTINCT s.id_sessio,s.unitat,s.data,s.dia, trim(d.docent) AS docent,
 bool_or(s.torn_requerit='mati') AS mati,
 bool_or(s.torn_requerit='tarda') AS tarda
 FROM sessions s,
 unnest(string_split(coalesce(s.docents,''),'|')) d(docent)
 WHERE s.sem=$semestre AND ($setmana IS NULL OR s.setmana=$setmana) AND trim(d.docent)<>''
 GROUP BY s.id_sessio,s.unitat,s.data,s.dia,trim(d.docent)
), dies AS (
 SELECT docent,data,dia,bool_or(mati) AS mati,bool_or(tarda) AS tarda
 FROM docencia GROUP BY docent,data,dia
), resum AS (
 SELECT docent,bool_or(mati AND tarda) AS a_cavall,
 count(*) FILTER (WHERE mati AND tarda) AS dies_mati_tarda,
 string_agg(dia,', ' ORDER BY dia) FILTER (WHERE mati AND tarda) AS dies
 FROM dies GROUP BY docent
)
SELECT r.*, (SELECT list(DISTINCT id_sessio ORDER BY id_sessio) FROM docencia d
 WHERE d.docent=r.docent AND (d.mati OR d.tarda)) AS exemples
FROM resum r WHERE a_cavall ORDER BY dies_mati_tarda DESC,docent

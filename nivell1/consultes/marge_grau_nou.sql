-- Oferta màxima: es poden reservar les dues aules més petites a cada franja.
WITH llindars AS (
 SELECT DISTINCT capacitat AS llindar FROM aules WHERE ordinaria
 UNION SELECT 0
), base AS (
 SELECT unitat, max(alumnes) AS alumnes, max(durada_min)/60.0 AS hores
 FROM sessions WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana) AND demanda_aulari
 AND regexp_matches(titulacions_curs, ':(1r|2n)(\||$)') GROUP BY unitat
), nou AS (
 SELECT unitat, max(alumnes) AS alumnes, max(durada_min)/60.0 AS hores
 FROM grau_nou WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana) AND demanda_aulari
 GROUP BY unitat
), variants AS (SELECT false AS seminaris UNION ALL SELECT true), oferta AS (
 SELECT l.llindar, v.seminaris,
 (least(19, count(*) FILTER (WHERE a.ordinaria AND a.capacitat>l.llindar))
 + count(*) FILTER (WHERE v.seminaris AND a.tipus='Seminaris' AND a.capacitat>l.llindar))*30.0 * CASE WHEN $setmana IS NULL THEN
 (SELECT count(DISTINCT setmana) FROM sessions WHERE sem=$semestre) ELSE 1 END AS oferta_hores
 FROM llindars l CROSS JOIN variants v CROSS JOIN aules a GROUP BY 1,2
)
SELECT *, oferta_hores-demanda_hores AS marge_hores,
 oferta_hores-demanda_hores-nou_hores AS saldo_hores
FROM (
 SELECT o.*, coalesce((SELECT sum(hores) FROM base WHERE alumnes>o.llindar),0) AS demanda_hores,
 coalesce((SELECT sum(hores) FROM nou WHERE alumnes>o.llindar),0) AS nou_hores
 FROM oferta o
) ORDER BY seminaris, llindar

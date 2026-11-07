-- Oferta màxima: reserva de les dues aules més petites per franja.
WITH llindars AS (
 SELECT DISTINCT capacitat AS llindar FROM aules WHERE ordinaria
 UNION SELECT 0
), base AS (
 SELECT unitat, sum(alumnes) AS alumnes, max(durada_min)/60.0 AS hores
 FROM sessions WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana)
 AND demanda_aulari AND torn_requerit='mati' GROUP BY unitat
), nou AS (
 SELECT unitat, sum(alumnes) AS alumnes, max(durada_min)/60.0 AS hores
 FROM grau_nou WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana)
 AND demanda_aulari AND torn_requerit='mati' GROUP BY unitat
), setmanes AS (
 SELECT DISTINCT setmana FROM sessions WHERE sem=$semestre
 AND ($setmana IS NULL OR setmana=$setmana)
), dates AS (
 SELECT CAST(strptime(setmana || '-1', '%G-W%V-%u') AS DATE) + CAST(d AS INTEGER) AS data
 FROM setmanes CROSS JOIN range(5) dies(d)
), aturades AS (
 SELECT data,
 coalesce(try_cast(split_part(h_ini, ':', 1) AS INTEGER)*60
          +try_cast(split_part(h_ini, ':', 2) AS INTEGER),0) AS ini,
 coalesce(try_cast(split_part(h_fi, ':', 1) AS INTEGER)*60
          +try_cast(split_part(h_fi, ':', 2) AS INTEGER),1440) AS fi
 FROM calendari
), temps AS (
 -- Minuts disponibles: les aturades solapades es descompten un sol cop.
 SELECT count(*)/60.0 AS hores FROM dates CROSS JOIN range(510,870) minuts(m)
 WHERE NOT EXISTS (SELECT 1 FROM aturades a WHERE a.data=dates.data AND m>=a.ini AND m<a.fi)
), variants AS (SELECT false AS seminaris UNION ALL SELECT true), oferta AS (
 SELECT l.llindar, v.seminaris,
 (least(19, count(*) FILTER (WHERE a.ordinaria AND a.capacitat>l.llindar))
 + count(*) FILTER (WHERE v.seminaris AND a.tipus='Seminaris' AND a.capacitat>l.llindar))
 * (SELECT hores FROM temps) AS oferta_hores
 FROM llindars l CROSS JOIN variants v CROSS JOIN aules a GROUP BY 1,2
)
SELECT *, oferta_hores-demanda_hores AS marge_hores,
 oferta_hores-demanda_hores-nou_hores AS saldo_hores
FROM (
 SELECT o.*, coalesce((SELECT sum(hores) FROM base WHERE o.llindar=0 OR alumnes>o.llindar),0) AS demanda_hores,
 coalesce((SELECT sum(hores) FROM nou WHERE o.llindar=0 OR alumnes>o.llindar),0) AS nou_hores
 FROM oferta o
) ORDER BY seminaris, llindar

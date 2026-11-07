-- Capa c: oferta optimista amb reserva flexible de dues aules ordinàries.
-- Cada llindar és una condició necessària; superar-les no prova un horari viable.
WITH unitats AS (
 SELECT unitat, sum(alumnes) AS alumnes, max(durada_min)/60.0 AS hores
 FROM sessions WHERE sem=$semestre AND setmana=$setmana AND demanda_aulari
 AND regexp_matches(titulacions_curs, ':(1r|2n)(\||$)') GROUP BY unitat
), llindars AS (
 SELECT DISTINCT capacitat AS llindar FROM aules WHERE tipus='Aules docents'
), demanda AS (
 SELECT k.llindar, coalesce(sum(u.hores),0) AS demanda_h
 FROM llindars k LEFT JOIN unitats u ON u.alumnes>k.llindar GROUP BY k.llindar
), oferta AS (
 SELECT k.llindar,
   least(19,count(*) FILTER(WHERE a.tipus='Aules docents'))*30 AS oferta_h,
   (least(19,count(*) FILTER(WHERE a.tipus='Aules docents'))+
    count(*) FILTER(WHERE a.tipus='Seminaris'))*30 AS oferta_h_amb_seminaris
 FROM llindars k LEFT JOIN aules a ON a.capacitat>k.llindar
 AND a.tipus IN ('Aules docents','Seminaris') GROUP BY k.llindar
)
SELECT *, demanda_h>oferta_h AS falla,
 demanda_h>oferta_h_amb_seminaris AS falla_amb_seminaris
FROM demanda JOIN oferta USING(llindar) ORDER BY llindar;

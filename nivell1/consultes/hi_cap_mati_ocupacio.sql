-- Capa b: tota la durada de 1r i 2n, inclosa la tarda que cal traslladar.
WITH unitats AS (
 SELECT unitat, max(durada_min)/60.0 AS hores, min(id_sessio) AS exemple
 FROM sessions WHERE sem=$semestre AND setmana=$setmana AND demanda_aulari
 AND regexp_matches(titulacions_curs, ':(1r|2n)(\||$)') GROUP BY unitat
)
SELECT coalesce(sum(hores),0) AS demanda_h, 19*5*6 AS oferta_h,
       27*5*6 AS oferta_h_amb_seminaris,
       100*coalesce(sum(hores),0)/(19*5*6) AS ocupacio_pct,
       coalesce(list(exemple ORDER BY exemple), []::VARCHAR[]) AS exemples FROM unitats;

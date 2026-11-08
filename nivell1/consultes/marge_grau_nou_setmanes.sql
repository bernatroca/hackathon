-- Criteri propi del grau nou: més hores-aula de matí de l'horari existent.
WITH unitats AS (
 SELECT setmana, unitat, max(CASE WHEN demanda_aulari AND torn_requerit='mati'
 THEN durada_min ELSE 0 END)/60.0 AS hores
 FROM sessions WHERE sem=$semestre GROUP BY setmana,unitat
)
SELECT setmana, sum(hores) AS demanda_hores FROM unitats
GROUP BY setmana ORDER BY demanda_hores DESC, setmana;

-- Ocupacions físiques: les compartides compten un cop per aula i bloc.
WITH triades AS (
    SELECT * FROM sessions WHERE sem = $semestre AND ($setmana IS NULL OR setmana = $setmana)
), espais AS (
    SELECT s.*, unnest(list_distinct(list_filter(
        list_prepend(aula_partida, string_split(coalesce(aules_addicionals_partida, ''), '|')),
        lambda x: x IS NOT NULL AND x <> ''))) AS aula
    FROM triades s WHERE NOT sense_espai AND aula_partida IS NOT NULL
    UNION ALL
    SELECT *, 'sense aula' AS aula FROM triades WHERE aula_partida IS NULL
), inventari AS (
    SELECT aula FROM aules UNION SELECT aula FROM espais UNION SELECT 'sense aula'
)
SELECT i.aula, 100.0 * count(DISTINCT (e.data, sb.bloc)) FILTER (WHERE sb.bloc IS NOT NULL)
 / nullif((SELECT count(DISTINCT setmana) FROM triades) * 125, 0) AS percent_ocupacio
FROM inventari i LEFT JOIN espais e ON e.aula = i.aula
LEFT JOIN sessio_blocs sb USING (id_sessio)
WHERE i.aula <> 'sense aula'
GROUP BY i.aula ORDER BY percent_ocupacio DESC NULLS LAST, aula;

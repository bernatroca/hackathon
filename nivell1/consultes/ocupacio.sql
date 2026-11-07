-- Ocupacions físiques: les compartides compten un cop per aula i bloc.
WITH triades AS (
    SELECT * FROM sessions WHERE sem = $semestre AND setmana = $setmana
), espais AS (
    SELECT s.*, unnest(list_distinct(list_filter(
        list_prepend(aula_partida, string_split(coalesce(aules_addicionals_partida, ''), '|')),
        lambda x: x IS NOT NULL AND x <> ''))) AS aula
    FROM triades s WHERE NOT sense_espai AND aula_partida IS NOT NULL
    UNION ALL
    SELECT *, 'sense aula' AS aula FROM triades WHERE aula_partida IS NULL
), inventari AS (
    SELECT aula FROM aules UNION SELECT aula FROM espais UNION SELECT 'sense aula'
), dies AS (
    SELECT * FROM (VALUES ('L', 1), ('M', 2), ('X', 3), ('J', 4), ('V', 5)) t(dia, ordre)
), ocupades AS (
    SELECT e.aula, e.dia, sb.bloc, count(DISTINCT e.unitat) AS valor,
           list_sort(list(DISTINCT e.id_sessio)) AS exemples
    FROM espais e JOIN sessio_blocs sb USING (id_sessio)
    GROUP BY e.aula, e.dia, sb.bloc
), mapa AS (
    SELECT i.aula, d.dia, d.ordre, b.bloc, b.etiqueta,
           coalesce(o.valor, 0) AS valor, o.exemples
    FROM inventari i CROSS JOIN dies d CROSS JOIN blocs b
    LEFT JOIN ocupades o ON o.aula = i.aula AND o.dia = d.dia AND o.bloc = b.bloc
)
SELECT *, 100.0 * count(*) FILTER (WHERE valor > 0) OVER (PARTITION BY aula) / 125 AS percent_ocupacio
FROM mapa ORDER BY percent_ocupacio DESC, aula, ordre, bloc;

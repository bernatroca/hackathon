-- La cobertura documental és de tot el semestre; la demanda és de la setmana triada.
WITH resum AS (
    SELECT count(*) AS sessions_totals,
           count(*) FILTER (WHERE aula_partida IS NULL) AS sense_aula,
           count(*) FILTER (WHERE aula_partida IS NULL AND demanda_aulari) AS per_assignar,
           count(*) FILTER (WHERE aula_partida IS NULL AND sense_espai) AS dobles,
           count(*) FILTER (WHERE aula_partida IS NULL AND tipus = 'PLAB') AS plab,
           list_sort(list(id_sessio) FILTER (WHERE aula_partida IS NULL)) AS exemples
    FROM sessions WHERE sem = $semestre
), dies AS (
    SELECT * FROM (VALUES ('L', 1), ('M', 2), ('X', 3), ('J', 4), ('V', 5)) t(dia, ordre)
), demanda AS (
    SELECT s.dia, sb.bloc, count(DISTINCT s.unitat) AS demanda
    FROM sessions s JOIN sessio_blocs sb USING (id_sessio)
    WHERE s.sem = $semestre AND s.setmana = $setmana AND s.demanda_aulari
    GROUP BY s.dia, sb.bloc
)
SELECT d.dia, b.bloc, b.etiqueta, b.franja, coalesce(n.demanda, 0) AS demanda,
       (SELECT count(*) - 2 FROM aules WHERE tipus = 'Aules docents') AS disponibles,
       (SELECT count(*) - 2 FROM aules WHERE tipus IN ('Aules docents', 'Seminaris')) AS disponibles_amb_seminaris,
       0.5 * coalesce(n.demanda, 0) AS hores_demanda,
       r.*
FROM dies d CROSS JOIN blocs b CROSS JOIN resum r
LEFT JOIN demanda n ON n.dia = d.dia AND n.bloc = b.bloc
ORDER BY d.ordre, b.bloc;

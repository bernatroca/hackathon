-- Mateixa agrupació que _compartides_i_aforament del verificador oficial.
-- NULL a setmana permet comprovar el semestre sencer.
WITH grups AS (
    SELECT s.unitat, s.aula_partida AS aula, min(s.data) AS data,
           min(s.dia) AS dia, min(s.h_ini) AS h_ini,
           sum(s.alumnes) AS alumnes, a.capacitat,
           bool_and(coalesce(s.fixada, '') <> '') AS heretada,
           list_sort(list(s.id_sessio)) AS exemples,
           list_distinct(list(s.codi || '/' || s.grup)) AS grups,
           count(*) FILTER (WHERE s.alumnes_origen = 'sense_dada') AS sense_dada
    FROM sessions s JOIN aules a ON a.aula = s.aula_partida
    WHERE s.sem = $semestre AND ($setmana IS NULL OR s.setmana = $setmana)
          AND NOT s.sense_espai
    GROUP BY s.unitat, s.aula_partida, a.capacitat
)
SELECT *, alumnes > capacitat AS supera, greatest(alumnes - capacitat, 0) AS exces
FROM grups ORDER BY exces DESC, data, h_ini, aula, unitat;

-- Capa a: hores actuals; una compartida és una classe.
WITH dies AS (
 SELECT DISTINCT data, dia FROM sessions WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana)
), demanda AS (
 SELECT s.data, sb.bloc, count(DISTINCT unitat) AS classes,
        list(DISTINCT s.id_sessio ORDER BY s.id_sessio) AS exemples
 FROM sessions s JOIN sessio_blocs sb USING(id_sessio)
 WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana) AND demanda_aulari
   AND torn_requerit='mati'
 GROUP BY s.data, sb.bloc
)
SELECT d.data, d.dia, b.bloc, b.etiqueta, coalesce(n.classes,0) AS classes,
       19 AS aules, 27 AS aules_amb_seminaris, n.exemples
FROM dies d CROSS JOIN blocs b LEFT JOIN demanda n ON n.data=d.data AND n.bloc=b.bloc
WHERE b.franja='mati' ORDER BY d.data,b.bloc;

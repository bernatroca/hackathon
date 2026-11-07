-- Incloem totes les setmanes amb sessions, també les que no tenen incidències.
SELECT count(DISTINCT setmana) AS setmanes FROM sessions
WHERE sem = $semestre AND ($setmana IS NULL OR setmana = $setmana);

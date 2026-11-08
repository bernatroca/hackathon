-- Setmana lectiva: almenys la meitat de sessions de la setmana amb més classes.
WITH recomptes AS (
 SELECT setmana, count(*) AS classes FROM sessions WHERE sem=$semestre GROUP BY setmana
), lectives AS (
 SELECT setmana FROM recomptes WHERE classes >= (SELECT max(classes)*0.5 FROM recomptes)
)
SELECT count(*) AS setmanes FROM lectives
WHERE ($setmana IS NULL OR setmana=$setmana);

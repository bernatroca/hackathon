-- Les dobles de cursos superiors al matí són el subconjunt de 248 R1-TORN.
-- No hi ha una clau que acrediti amb quin altre grup assisteixen.
SELECT id_sessio, unitat, titulacions_curs AS cohort, tipus, durada_min,
 CASE WHEN tipus <> 'PLAB' THEN durada_min / 60.0 ELSE 0 END AS hores_separacio
FROM sessions
WHERE sem = $semestre AND ($setmana IS NULL OR setmana = $setmana)
 AND sense_espai AND torn_requerit = 'tarda' AND ini_min < 870
 AND coalesce(fixada, '') = ''
ORDER BY id_sessio

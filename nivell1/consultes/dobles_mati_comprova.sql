SELECT count(*) AS fora_torn FROM sessions
WHERE sem = $semestre AND ($setmana IS NULL OR setmana = $setmana)
AND coalesce(fixada, '') = ''
AND ((torn_requerit='mati' AND ini_min>=870)
 OR (torn_requerit='tarda' AND ini_min<870))

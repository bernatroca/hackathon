-- Mateix conjunt que sessions a fora_torn.sql: exclou les fixades.
SELECT id_sessio, assignatura, grup, data, dia, h_ini, h_fi, titulacions_curs,
       torn_actual, torn_requerit
FROM sessions
WHERE sem = $semestre AND torn_requerit IN ('mati', 'tarda')
  AND torn_requerit <> torn_actual AND coalesce(fixada, '') = ''
ORDER BY data, h_ini, assignatura, grup, id_sessio;

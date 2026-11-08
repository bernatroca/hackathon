-- Mateix conjunt que per_assignar a hores_aula.sql: tot el semestre.
SELECT id_sessio, assignatura, grup, data, dia, h_ini, h_fi, titulacions_curs
FROM sessions
WHERE sem = $semestre AND aula_partida IS NULL AND demanda_aulari
ORDER BY data, h_ini, assignatura, grup, id_sessio;

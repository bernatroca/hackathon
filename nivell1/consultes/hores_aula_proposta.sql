-- Mateix conjunt que per_assignar a hores_aula.sql, amb l'aula proposada.
SELECT count(*) AS pendents
FROM sessions s
LEFT JOIN read_csv($proposta, header=true, all_varchar=true) p USING (id_sessio)
WHERE s.sem = $semestre AND s.demanda_aulari AND coalesce(p.aula, '') = '';

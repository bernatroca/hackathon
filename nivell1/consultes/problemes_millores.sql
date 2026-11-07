-- Les categories se solapen: les seves xifres no s'han de sumar.
WITH base AS (
 SELECT s.*,a.tipus AS tipus_aula FROM sessions s LEFT JOIN aules a ON a.aula=s.aula_partida
 WHERE s.sem=$semestre AND ($setmana IS NULL OR s.setmana=$setmana)
), grups AS (
 SELECT *, split_part(grup,'/',-1) AS num_grup,
 CASE WHEN length(split_part(grup,'/',-1))>=3 AND (tipus<>'TE' OR ends_with(grup,'0'))
 THEN left(split_part(grup,'/',-1),-1) ELSE split_part(grup,'/',-1) END AS linia
 FROM base
), parells AS (
 SELECT a.*, b.id_sessio AS altre_id, b.unitat AS altra_unitat,
 b.docents AS altres_docents, b.titulacions_curs AS altres_cohorts,
 b.tipus AS altre_tipus,b.num_grup AS altre_grup,b.linia AS altra_linia
 FROM grups a JOIN grups b ON a.data=b.data AND a.ini_min<b.fi_min AND b.ini_min<a.fi_min
 AND a.id_sessio<b.id_sessio AND a.unitat<>b.unitat
), aforament AS (
 SELECT unitat,aula_partida FROM base WHERE NOT sense_espai AND tipus_aula IS NOT NULL
 GROUP BY unitat,aula_partida HAVING sum(alumnes)>(SELECT capacitat FROM aules WHERE aula=aula_partida)
), incidencies AS (
 SELECT 'Sessions sense aula' AS problema,unitat,id_sessio FROM base
 WHERE demanda_aulari AND aula_partida IS NULL
 UNION ALL SELECT 'PAUL en laboratoris de Q6',unitat,id_sessio FROM base
 WHERE tipus='PAUL' AND tipus_aula='Laboratoris docents' AND starts_with(aula_partida,'Q6/') AND NOT sense_espai
 UNION ALL SELECT 'Sessions fora de la finestra',unitat,id_sessio FROM base
 WHERE NOT ((ini_min>=510 AND fi_min<=870) OR (ini_min>=870 AND fi_min<=1260))
 UNION ALL SELECT 'Sessions a aules J',unitat,id_sessio FROM base
 WHERE starts_with(aula_partida,'J/') AND NOT sense_espai
 UNION ALL SELECT 'Sessions fora de l’inventari',unitat,id_sessio FROM base
 WHERE aula_partida IS NOT NULL AND tipus_aula IS NULL AND NOT sense_espai
 UNION ALL SELECT 'Sessions sense dada d’alumnes',unitat,id_sessio FROM base
 WHERE alumnes=0 AND NOT sense_espai
 UNION ALL SELECT 'Més alumnes que places',b.unitat,b.id_sessio FROM base b
 JOIN aforament a USING(unitat,aula_partida)
 UNION ALL SELECT 'Solapaments de docent heretats',
 least(unitat,altra_unitat)||'|'||greatest(unitat,altra_unitat)||'|'||d.docent,id_sessio
 FROM parells, unnest(string_split(coalesce(docents,''),'|')) d(docent)
 WHERE d.docent<>'' AND list_contains(string_split(coalesce(altres_docents,''),'|'),d.docent)
 UNION ALL SELECT 'Solapaments d’alumnat heretats',
 least(unitat,altra_unitat)||'|'||greatest(unitat,altra_unitat),id_sessio FROM parells
 WHERE len(list_intersect(string_split(coalesce(titulacions_curs,''),'|'), string_split(coalesce(altres_cohorts,''),'|')))>0
 AND (CASE WHEN tipus='TE' OR altre_tipus='TE' THEN linia=altra_linia OR num_grup=altre_grup ELSE num_grup=altre_grup END)
), definicions(problema,com_es_calcula,proposta) AS (VALUES
 ('Més alumnes que places','Classes físiques amb suma d’alumnes de les sessions compartides superior a la capacitat; exclou dobles. Detall: aforament.','Assignar una aula amb prou places o revisar la composició dels grups.'),
 ('Solapaments de docent heretats','Parells de classes físiques solapades per docent, com R4-DOCENT; docents assignats al grup.','Confirmar qui imparteix cada sessió i separar els conflictes reals.'),
 ('Solapaments d’alumnat heretats','Parells de classes físiques solapades amb cohort comuna i mateixa línia si hi ha TE, o mateix número de grup, com R4-ALUMNAT.','Revisar matrícula i optatives; separar els conflictes confirmats.'),
 ('Sessions sense aula','Classes físiques que demanen aulari i no tenen aula; exclou PLAB i dobles. Vegeu hores-aula.','Assignar aula segons mida i equipament abans de validar la proposta.'),
 ('PAUL en laboratoris de Q6','Classes físiques PAUL en laboratoris docents Q6; exclou dobles sense espai propi.','Traslladar-les a aules docents o seminaris compatibles.'),
 ('Sessions fora de la finestra','Classes físiques que no caben senceres a 8.30–14.30 o 14.30–21.00, incloses les que travessen les 14.30.','Reprogramar cada sessió dins una única finestra completa.'),
 ('Sessions a aules J','Classes físiques amb aula J; exclou dobles sense espai propi.','Portar-les a l’aulari de l’Escola amb mida i equipament compatibles.'),
 ('Sessions fora de l’inventari','Classes físiques amb aula principal absent de l’inventari; inclou J i exclou dobles.','Revisar les J per traslladar-les; conservar B3/0021 i QC/1082 només per a les sessions actuals.'),
 ('Sessions sense dada d’alumnes','Classes físiques amb alumnes = 0, excloses les dobles sense espai propi.','Completar la matrícula o l’estimació abans de comprovar l’aforament.')
)
SELECT d.problema,count(DISTINCT i.unitat) AS xifra,d.com_es_calcula,d.proposta,
 coalesce(list(DISTINCT i.id_sessio ORDER BY i.id_sessio) FILTER (WHERE i.id_sessio IS NOT NULL), []) AS exemples
FROM definicions d LEFT JOIN incidencies i USING(problema)
GROUP BY d.problema,d.com_es_calcula,d.proposta ORDER BY xifra DESC,problema

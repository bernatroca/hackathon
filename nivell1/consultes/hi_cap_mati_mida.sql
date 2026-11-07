WITH setmanes AS (
 SELECT DISTINCT setmana, date_trunc('week',data)::DATE AS dilluns
 FROM sessions WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana)
), torns(torn,ini,fi,variant) AS (
 VALUES ('mati',510,870,'oficial'),('tarda',870,1260,'oficial'),
        ('tarda',900,1260,'15-21')
), minuts AS (
 -- Minuts disponibles: NOT EXISTS evita descomptar dues vegades aturades solapades.
 SELECT w.setmana,t.torn,t.variant,count(*)/60.0 AS hores_torn
 FROM setmanes w CROSS JOIN torns t CROSS JOIN range(5) d(i)
 CROSS JOIN range(510,1260) m(minut)
 WHERE m.minut>=t.ini AND m.minut<t.fi AND NOT EXISTS (
  SELECT 1 FROM calendari c WHERE c.data=w.dilluns+CAST(d.i AS INTEGER)
  AND c.tipus IN ('festiu','no_lectiu','aturada')
  AND m.minut>=coalesce(60*try_cast(split_part(c.h_ini,':',1) AS INTEGER)
                           +try_cast(split_part(c.h_ini,':',2) AS INTEGER),0)
  AND m.minut<coalesce(60*try_cast(split_part(c.h_fi,':',1) AS INTEGER)
                          +try_cast(split_part(c.h_fi,':',2) AS INTEGER),1440)
 ) GROUP BY w.setmana,t.torn,t.variant
), oferta_torn AS (
 SELECT w.setmana,t.torn,t.variant,coalesce(m.hores_torn,0) AS hores_torn
 FROM setmanes w CROSS JOIN torns t LEFT JOIN minuts m USING(setmana,torn,variant)
), unitats AS (
 SELECT s.setmana,s.torn_requerit AS torn,s.unitat,sum(s.alumnes) AS alumnes,
 max(s.durada_min)/60.0 AS hores,min(s.id_sessio) AS exemple,
 max(CASE WHEN s.torn_actual=s.torn_requerit THEN s.durada_min ELSE 0 END)/60.0 AS hores_avui
 FROM sessions s WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana)
 AND demanda_aulari AND torn_requerit IN ('mati','tarda')
 GROUP BY s.setmana,s.torn_requerit,s.unitat
)
, llindars AS (
 SELECT DISTINCT capacitat AS llindar FROM aules WHERE tipus='Aules docents'
), capacitats AS (
 SELECT k.llindar,
 least(19,count(*) FILTER(WHERE a.tipus='Aules docents')) AS aules,
 least(19,count(*) FILTER(WHERE a.tipus='Aules docents'))+
 count(*) FILTER(WHERE a.tipus='Seminaris') AS aules_amb_seminaris
 FROM llindars k LEFT JOIN aules a ON a.capacitat>k.llindar
 AND a.tipus IN ('Aules docents','Seminaris') GROUP BY k.llindar
), resultat AS (
 SELECT o.*,k.llindar,coalesce(sum(u.hores),0) AS demanda_h,
 o.hores_torn*k.aules AS oferta_h,
 o.hores_torn*k.aules_amb_seminaris AS oferta_h_amb_seminaris
 FROM oferta_torn o CROSS JOIN capacitats k LEFT JOIN unitats u
 ON u.setmana=o.setmana AND u.torn=o.torn AND u.alumnes>k.llindar
 GROUP BY ALL
)
SELECT *,demanda_h>oferta_h AS falla,
 demanda_h>oferta_h_amb_seminaris AS falla_amb_seminaris,
 oferta_h-demanda_h AS marge_h,
 CASE WHEN oferta_h>0 THEN 100*(oferta_h-demanda_h)/oferta_h
      WHEN demanda_h>0 THEN '-Infinity'::DOUBLE ELSE NULL END AS marge_pct
FROM resultat ORDER BY torn,variant,setmana,llindar;

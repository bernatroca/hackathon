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
, demanda AS (
 SELECT setmana,torn,sum(hores) AS demanda_h,sum(hores_avui) AS demanda_h_avui,
 count(*) FILTER(WHERE alumnes=0) AS unitats_mida_desconeguda,
 coalesce(list(exemple ORDER BY exemple), []::VARCHAR[]) AS exemples
 FROM unitats GROUP BY setmana,torn
), resultat AS (
 SELECT o.*,coalesce(d.demanda_h,0) AS demanda_h,coalesce(d.demanda_h_avui,0) AS demanda_h_avui,
 coalesce(d.unitats_mida_desconeguda,0) AS unitats_mida_desconeguda,
 coalesce(d.exemples,[]::VARCHAR[]) AS exemples,
 19*hores_torn AS oferta_h,27*hores_torn AS oferta_h_amb_seminaris,
 CASE WHEN hores_torn>0 THEN 100*coalesce(d.demanda_h,0)/(19*hores_torn)
      WHEN coalesce(d.demanda_h,0)>0 THEN 'Infinity'::DOUBLE ELSE 0 END AS ocupacio_pct
 FROM oferta_torn o LEFT JOIN demanda d USING(setmana,torn)
)
SELECT *,median(ocupacio_pct) OVER(PARTITION BY torn,variant) AS ocupacio_mediana_pct,
 row_number() OVER(PARTITION BY torn,variant ORDER BY ocupacio_pct DESC,setmana) AS ordre_pitjor
FROM resultat ORDER BY torn,variant,ordre_pitjor;

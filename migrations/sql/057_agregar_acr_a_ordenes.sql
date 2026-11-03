-- =============================================================================
-- 057 · Agregar RELACIÓN ALBUMINURIA/CREATINURIA ACR a las órdenes que tienen
--       CREATININA EN ORINA PARCIAL y MICROALBUMINURIA AUTOMATIZADA EN ORINA PARCIAL
-- =============================================================================
--
-- - La prueba ACR se crea en blanco (Sin resultados) dentro del estudio de
--   Microalbuminuria, como está en su configuración (prueba no requerida, así
--   que no cambia el estado de la orden).
-- - Omite órdenes anuladas, estudios anulados y órdenes que ya tienen ACR (en
--   cualquier estudio, p. ej. si se pidió el estudio ACR aparte).
-- - Se puede correr varias veces sin duplicar.
-- Ejecutar completo en pgAdmin (F5) o con psql.
-- =============================================================================


-- 0. Órdenes a las que se les agregará (antes)
SELECT o.o_id, o.o_number, o.o_order_state, dm.od_id AS od_microalbuminuria
FROM "Orders" o
JOIN "OrdersDetails" dm ON dm.od_order_id = o.o_id AND dm.od_cancelled = 0
JOIN "StudiesLab" sm    ON sm.id = dm.od_study_id AND sm.name = 'MICROALBUMINURIA AUTOMATIZADA EN ORINA PARCIAL'
JOIN "TestsLab" t       ON t.name = 'RELACIÓN ALBUMINURIA/CREATINURIA ACR'
WHERE o.o_order_state <> 7
  AND EXISTS (SELECT 1 FROM "OrdersDetails" dc JOIN "StudiesLab" sc ON sc.id = dc.od_study_id
              WHERE dc.od_order_id = o.o_id AND dc.od_cancelled = 0
                AND sc.name = 'CREATININA EN ORINA PARCIAL')
  AND NOT EXISTS (SELECT 1 FROM "Laboratories" l JOIN "OrdersDetails" x ON x.od_id = l.l_order_detail_id
                  WHERE x.od_order_id = o.o_id AND x.od_cancelled = 0 AND l.l_test_id = t.id)
ORDER BY o.o_id;


-- 1. Crear la prueba ACR en blanco (l_state 0 = Sin resultados)
INSERT INTO "Laboratories" (l_order_detail_id, l_test_id, l_state, l_created_at, l_updated_at)
SELECT dm.od_id, t.id, 0,
       now() AT TIME ZONE 'America/Bogota', now() AT TIME ZONE 'America/Bogota'
FROM "Orders" o
JOIN "OrdersDetails" dm ON dm.od_order_id = o.o_id AND dm.od_cancelled = 0
JOIN "StudiesLab" sm    ON sm.id = dm.od_study_id AND sm.name = 'MICROALBUMINURIA AUTOMATIZADA EN ORINA PARCIAL'
JOIN "TestsLab" t       ON t.name = 'RELACIÓN ALBUMINURIA/CREATINURIA ACR'
WHERE o.o_order_state <> 7
  AND EXISTS (SELECT 1 FROM "OrdersDetails" dc JOIN "StudiesLab" sc ON sc.id = dc.od_study_id
              WHERE dc.od_order_id = o.o_id AND dc.od_cancelled = 0
                AND sc.name = 'CREATININA EN ORINA PARCIAL')
  AND NOT EXISTS (SELECT 1 FROM "Laboratories" l JOIN "OrdersDetails" x ON x.od_id = l.l_order_detail_id
                  WHERE x.od_order_id = o.o_id AND x.od_cancelled = 0 AND l.l_test_id = t.id);


-- 2. Verificación: debe devolver 0 filas
SELECT o.o_number
FROM "Orders" o
JOIN "OrdersDetails" dm ON dm.od_order_id = o.o_id AND dm.od_cancelled = 0
JOIN "StudiesLab" sm    ON sm.id = dm.od_study_id AND sm.name = 'MICROALBUMINURIA AUTOMATIZADA EN ORINA PARCIAL'
JOIN "TestsLab" t       ON t.name = 'RELACIÓN ALBUMINURIA/CREATINURIA ACR'
WHERE o.o_order_state <> 7
  AND EXISTS (SELECT 1 FROM "OrdersDetails" dc JOIN "StudiesLab" sc ON sc.id = dc.od_study_id
              WHERE dc.od_order_id = o.o_id AND dc.od_cancelled = 0
                AND sc.name = 'CREATININA EN ORINA PARCIAL')
  AND NOT EXISTS (SELECT 1 FROM "Laboratories" l JOIN "OrdersDetails" x ON x.od_id = l.l_order_detail_id
                  WHERE x.od_order_id = o.o_id AND x.od_cancelled = 0 AND l.l_test_id = t.id);

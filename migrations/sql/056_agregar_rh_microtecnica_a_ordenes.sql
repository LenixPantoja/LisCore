-- =============================================================================
-- 056 · Agregar la prueba HEMOCLASIFICACION FACTOR RH MICROTECNICA a las órdenes
--       que tienen el estudio HEMOCLASIFICACION ABO DIRECTA MICROTECNICA
-- =============================================================================
--
-- La prueba se agregó a la configuración del estudio después de crear algunas
-- órdenes; esas órdenes quedaron solo con la prueba ABO. Este script les crea
-- la prueba que falta, en blanco (Sin resultados), igual que al crear una orden.
--
-- - Se buscan estudio y prueba por nombre (sirve en otras bases de clientes).
-- - Omite estudios anulados y los que ya tienen la prueba: se puede correr
--   varias veces sin duplicar.
-- - No crea muestras: verifique con el bloque 0 que cada orden tenga la muestra
--   del tipo de la prueba (columna tiene_muestra = true).
--
-- Ejecutar completo en pgAdmin (F5) o con psql.
-- =============================================================================


-- 0. Órdenes a las que les falta la prueba (antes)
SELECT o.o_id, o.o_number, o.o_order_state, d.od_id,
       EXISTS (SELECT 1 FROM "SamplesOrder" so
               WHERE so.so_order_id = o.o_id AND so.so_sample_type_id = t.samples_type_id) AS tiene_muestra
FROM "OrdersDetails" d
JOIN "Orders" o      ON o.o_id = d.od_order_id
JOIN "StudiesLab" s  ON s.id = d.od_study_id
JOIN "TestsLab" t    ON t.name = 'HEMOCLASIFICACION FACTOR RH MICROTECNICA'
WHERE s.name = 'HEMOCLASIFICACION ABO DIRECTA MICROTECNICA'
  AND d.od_cancelled = 0
  AND NOT EXISTS (SELECT 1 FROM "Laboratories" l
                  WHERE l.l_order_detail_id = d.od_id AND l.l_test_id = t.id)
ORDER BY o.o_id;


-- 1. Crear la prueba en blanco (l_state 0 = Sin resultados)
INSERT INTO "Laboratories" (l_order_detail_id, l_test_id, l_state, l_created_at, l_updated_at)
SELECT d.od_id, t.id, 0,
       now() AT TIME ZONE 'America/Bogota', now() AT TIME ZONE 'America/Bogota'
FROM "OrdersDetails" d
JOIN "StudiesLab" s ON s.id = d.od_study_id
JOIN "TestsLab" t   ON t.name = 'HEMOCLASIFICACION FACTOR RH MICROTECNICA'
WHERE s.name = 'HEMOCLASIFICACION ABO DIRECTA MICROTECNICA'
  AND d.od_cancelled = 0
  AND NOT EXISTS (SELECT 1 FROM "Laboratories" l
                  WHERE l.l_order_detail_id = d.od_id AND l.l_test_id = t.id);


-- 2. Verificación: todas las órdenes del estudio deben tener la prueba (0 filas)
SELECT o.o_number, d.od_id
FROM "OrdersDetails" d
JOIN "Orders" o     ON o.o_id = d.od_order_id
JOIN "StudiesLab" s ON s.id = d.od_study_id
JOIN "TestsLab" t   ON t.name = 'HEMOCLASIFICACION FACTOR RH MICROTECNICA'
WHERE s.name = 'HEMOCLASIFICACION ABO DIRECTA MICROTECNICA'
  AND d.od_cancelled = 0
  AND NOT EXISTS (SELECT 1 FROM "Laboratories" l
                  WHERE l.l_order_detail_id = d.od_id AND l.l_test_id = t.id);

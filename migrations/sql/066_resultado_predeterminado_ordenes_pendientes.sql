-- =============================================================================
-- 066 - (OPCIONAL) Resultado predeterminado en órdenes que ya existen
-- =============================================================================
-- Desde esta versión, al crear una orden (o agregarle estudios), las pruebas
-- que tienen un formato de completado marcado como PREDETERMINADO nacen con
-- ese resultado y en estado "Con Resultados" (2), listas para validar.
--
-- Este script aplica lo mismo a las órdenes que YA existían y siguen
-- pendientes. Solo toca pruebas:
--   - sin resultado (l_result vacío) y en estado 0 "Sin Resultados",
--   - de órdenes no anuladas creadas en los últimos 7 días (ajuste el rango),
--   - cuya prueba tenga un formato predeterminado activo.
-- No modifica resultados ya digitados, validados ni de órdenes anuladas.
-- Seguro de correr varias veces.
-- =============================================================================

BEGIN;

WITH predeterminado AS (
    SELECT DISTINCT ON (x.tfc_testslab_id) x.tfc_testslab_id AS test_id, btrim(f.fc_name) AS valor
    FROM "TestslabFormatComplete" x
    JOIN "FormatComplete" f ON f.fc_id = x.tfc_format_complete_id
    WHERE x.tfc_is_default AND f.fc_active AND btrim(COALESCE(f.fc_name, '')) <> ''
    ORDER BY x.tfc_testslab_id, x.tfc_order_index, x.tfc_id
)
UPDATE "Laboratories" l
SET l_result     = p.valor,
    l_result_num = CASE WHEN replace(p.valor, ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
                        THEN replace(p.valor, ',', '.')::numeric END,
    l_state      = 2,
    l_updated_at = (now() AT TIME ZONE 'America/Bogota')
FROM predeterminado p, "OrdersDetails" od, "Orders" o
WHERE p.test_id = l.l_test_id
  AND od.od_id = l.l_order_detail_id
  AND o.o_id = od.od_order_id
  AND COALESCE(l.l_state, 0) = 0
  AND btrim(COALESCE(l.l_result, '')) = ''
  AND COALESCE(od.od_cancelled, 0) = 0
  AND COALESCE(o.o_cancelled, 0) = 0
  AND COALESCE(o.o_order_state, 0) <> 7
  AND o.o_created_at >= (now() AT TIME ZONE 'America/Bogota') - interval '7 days';

COMMIT;

-- Verificación: pruebas con formato predeterminado y cuántas quedaron con ese valor
SELECT t.code, f.fc_name AS predeterminado,
       count(l.*) FILTER (WHERE l.l_result = f.fc_name) AS resultados_con_predeterminado
FROM "TestslabFormatComplete" x
JOIN "FormatComplete" f ON f.fc_id = x.tfc_format_complete_id
JOIN "TestsLab" t ON t.id = x.tfc_testslab_id
LEFT JOIN "Laboratories" l ON l.l_test_id = t.id
WHERE x.tfc_is_default
GROUP BY t.code, f.fc_name
ORDER BY t.code;

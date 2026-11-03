-- =====================================================================
-- LIS CoreLab · 054 · Índices de rendimiento e integridad
-- =====================================================================
-- Solo AGREGA índices: no modifica ni borra datos.
-- Se puede ejecutar varias veces (IF NOT EXISTS).
-- CONCURRENTLY: crea cada índice sin bloquear la tabla (se puede correr con
-- el sistema en uso). Por eso NO debe ejecutarse dentro de BEGIN/COMMIT:
-- en pgAdmin desactive "Auto-commit OFF"/transacción, o use psql (ver README).
-- =====================================================================

-- ── 0. VERIFICACIÓN PREVIA (debe devolver 0 filas) ─────────────────────
-- Si devuelve filas, hay solicitudes del HIS duplicadas y el índice único
-- del paso 2 fallará: depúrelas primero (ver README).
SELECT io_number_request, count(*) AS veces
FROM "InboundOrders"
WHERE io_number_request IS NOT NULL
GROUP BY io_number_request
HAVING count(*) > 1;

-- ── 1. Índices de rendimiento ──────────────────────────────────────────
-- Órdenes
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_orders_o_number"          ON "public"."Orders" ("o_number");
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_orders_o_headquarter_id"  ON "public"."Orders" ("o_headquarter_id");
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_orders_o_his_id"          ON "public"."Orders" ("o_his_id");
-- Trazabilidad (tabla que crece rápido)
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_apptrace_order_test"      ON "public"."AppTrace" ("order_id", "test_id");
-- Estudios por área
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_studieslab_work_groups_id" ON "public"."StudiesLab" ("work_groups_id");
-- Muestras y facturación de una orden
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_samplesorder_so_order_id" ON "public"."SamplesOrder" ("so_order_id");
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_invoicesdetail_invd_order_detail_id" ON "public"."InvoicesDetail" ("invd_order_detail_id");
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_Invoices_inv_number"      ON "public"."Invoices" ("inv_number");
-- Integración HIS (Centralink)
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_inboundordersdetails_iod_inboundorder_id" ON "public"."InboundOrdersDetails" ("iod_inboundOrder_id");
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_inboundordersdetails_iod_laboratory_id"   ON "public"."InboundOrdersDetails" ("iod_laboratory_id");
-- Etiquetas
CREATE INDEX CONCURRENTLY IF NOT EXISTS "ix_barcodes_label_type"      ON "public"."barcodes" ("label_type");

-- ── 2. Índice de integridad ────────────────────────────────────────────
-- Evita registrar dos veces la misma solicitud del HIS.
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "ux_inboundorders_io_number_request" ON "public"."InboundOrders" ("io_number_request");

-- ── 3. Estadísticas actualizadas para el planificador ─────────────────
ANALYZE "public"."Orders";
ANALYZE "public"."AppTrace";
ANALYZE "public"."StudiesLab";
ANALYZE "public"."InboundOrders";
ANALYZE "public"."InboundOrdersDetails";

-- ── 4. VERIFICACIÓN FINAL (debe listar los 12 índices con valido = true) ─
SELECT c.relname AS indice, i.indisvalid AS valido
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
WHERE c.relname IN (
  'ix_orders_o_number', 'ix_orders_o_headquarter_id', 'ix_orders_o_his_id', 'ix_apptrace_order_test',
  'ix_studieslab_work_groups_id', 'ix_samplesorder_so_order_id', 'ix_invoicesdetail_invd_order_detail_id',
  'ix_Invoices_inv_number', 'ix_inboundordersdetails_iod_inboundorder_id', 'ix_inboundordersdetails_iod_laboratory_id',
  'ix_barcodes_label_type', 'ux_inboundorders_io_number_request'
)
ORDER BY 1;

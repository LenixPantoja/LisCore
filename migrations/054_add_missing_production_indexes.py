"""
Migration 054: índices que faltaban en producción.

Revisión de la base de producción (2026-11-02) antes de la salida en vivo:

1. Índices de migraciones anteriores que NO quedaron aplicados en producción
   (allí no existe la tabla alembic_version, las migraciones se aplicaron a mano):
     - ix_orders_o_headquarter_id          (048) filtro de órdenes por sede
     - ix_barcodes_label_type              (047)
     - ix_Invoices_inv_number              (007)
     - ux_inboundorders_io_number_request  (049) evita solicitudes HIS duplicadas.
       IMPORTANTE: si ya hay duplicados por io_number_request este CREATE UNIQUE
       INDEX falla; limpiarlos antes (ver la migración 049).

2. Índices nuevos para consultas muy frecuentes que hacían table scan:
     - Orders.o_number            búsqueda por número (Laboratorio, Plan de Trabajo, Resultados)
     - Orders.o_his_id            órdenes de un paciente
     - AppTrace(order_id, test_id) trazabilidad de la orden y de cada analito (tabla que crece rápido)
     - StudiesLab.work_groups_id  filtros por área
     - SamplesOrder.so_order_id   muestras de una orden
     - InvoicesDetail.invd_order_detail_id  anulación de estudios
     - InboundOrdersDetails.iod_inboundOrder_id / iod_laboratory_id  Centralink

Todo usa IF NOT EXISTS: se puede correr aunque ya esté aplicado.
"""

from alembic import op

revision = "054_add_missing_production_indexes"
down_revision = "053_add_barcodes_number_labels_print"
branch_labels = None
depends_on = None

INDEXES = [
    ('ix_orders_o_headquarter_id', 'CREATE INDEX IF NOT EXISTS "ix_orders_o_headquarter_id" ON "public"."Orders" ("o_headquarter_id")'),
    ('ix_barcodes_label_type', 'CREATE INDEX IF NOT EXISTS "ix_barcodes_label_type" ON "public"."barcodes" ("label_type")'),
    ('ix_Invoices_inv_number', 'CREATE INDEX IF NOT EXISTS "ix_Invoices_inv_number" ON "public"."Invoices" ("inv_number")'),
    ('ix_orders_o_number', 'CREATE INDEX IF NOT EXISTS "ix_orders_o_number" ON "public"."Orders" ("o_number")'),
    ('ix_orders_o_his_id', 'CREATE INDEX IF NOT EXISTS "ix_orders_o_his_id" ON "public"."Orders" ("o_his_id")'),
    ('ix_apptrace_order_test', 'CREATE INDEX IF NOT EXISTS "ix_apptrace_order_test" ON "public"."AppTrace" ("order_id", "test_id")'),
    ('ix_studieslab_work_groups_id', 'CREATE INDEX IF NOT EXISTS "ix_studieslab_work_groups_id" ON "public"."StudiesLab" ("work_groups_id")'),
    ('ix_samplesorder_so_order_id', 'CREATE INDEX IF NOT EXISTS "ix_samplesorder_so_order_id" ON "public"."SamplesOrder" ("so_order_id")'),
    ('ix_invoicesdetail_invd_order_detail_id', 'CREATE INDEX IF NOT EXISTS "ix_invoicesdetail_invd_order_detail_id" ON "public"."InvoicesDetail" ("invd_order_detail_id")'),
    ('ix_inboundordersdetails_iod_inboundorder_id', 'CREATE INDEX IF NOT EXISTS "ix_inboundordersdetails_iod_inboundorder_id" ON "public"."InboundOrdersDetails" ("iod_inboundOrder_id")'),
    ('ix_inboundordersdetails_iod_laboratory_id', 'CREATE INDEX IF NOT EXISTS "ix_inboundordersdetails_iod_laboratory_id" ON "public"."InboundOrdersDetails" ("iod_laboratory_id")'),
    ('ux_inboundorders_io_number_request', 'CREATE UNIQUE INDEX IF NOT EXISTS "ux_inboundorders_io_number_request" ON "public"."InboundOrders" ("io_number_request")'),
]


def upgrade():
    for _, sql in INDEXES:
        op.execute(sql + ";")


def downgrade():
    for name, _ in reversed(INDEXES):
        op.execute(f'DROP INDEX IF EXISTS "public"."{name}";')

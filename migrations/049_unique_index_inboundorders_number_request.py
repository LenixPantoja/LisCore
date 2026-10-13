"""
Migration 049: Unique index on InboundOrders.io_number_request.

El endpoint POST /Dinamica/Laboratorio/RegistrarSolicitud (InterfazDG) ya
valida en código que no exista un InboundOrder con el mismo io_number_request
antes de crear uno nuevo (ver registrar_solicitud_dg), pero esa validación
tiene una ventana de carrera entre el SELECT y el INSERT si el HIS reintenta
la misma solicitud casi al mismo tiempo. Este índice único (NULLs permitidos,
comportamiento estándar de Postgres) cierra esa ventana a nivel de base de
datos.

IMPORTANTE: antes de correr esta migración hay que limpiar los duplicados
existentes por io_number_request (ver incidente del 2026-10-12) — si quedan
duplicados, el CREATE UNIQUE INDEX falla.

Safe to run even if already applied.
"""

from alembic import op
import sqlalchemy as sa

revision = "049_unique_index_inboundorders_number_request"
down_revision = "048_add_index_orders_headquarter_id"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS "ux_inboundorders_io_number_request"
        ON "public"."InboundOrders" ("io_number_request")
        WHERE "io_number_request" IS NOT NULL;
    """)


def downgrade():
    op.execute('DROP INDEX IF EXISTS "ux_inboundorders_io_number_request";')

"""
Migration 031: Add io_service_code and io_service_name columns to InboundOrders table.

Almacenan el codigo y nombre de servicio recibidos en el XML de InterfazDG
(GESERCODIGO / GESERNOMBRE), usados para homologar con Services.code.

Safe to run even if the columns already exist.
"""

from alembic import op
import sqlalchemy as sa

revision = "031_add_service_code_name_to_inbound_orders"
down_revision = "030_add_lp_state_to_laboratory_preliminaries"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'InboundOrders'
                  AND column_name = 'io_service_code'
            ) THEN
                ALTER TABLE "public"."InboundOrders"
                ADD COLUMN "io_service_code" VARCHAR(500);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'InboundOrders'
                  AND column_name = 'io_service_name'
            ) THEN
                ALTER TABLE "public"."InboundOrders"
                ADD COLUMN "io_service_name" VARCHAR(500);
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE "public"."InboundOrders"
        DROP COLUMN IF EXISTS "io_service_code";
    """)
    op.execute("""
        ALTER TABLE "public"."InboundOrders"
        DROP COLUMN IF EXISTS "io_service_name";
    """)

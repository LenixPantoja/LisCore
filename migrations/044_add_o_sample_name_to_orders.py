"""
Migration 044: Add Orders.o_sample_name (optional string).

Permite capturar el nombre de la muestra al crear una orden. Campo opcional.

Safe to run even if already applied.
"""

from alembic import op
import sqlalchemy as sa

revision = "044_add_o_sample_name_to_orders"
down_revision = "043_gradilla_multiple_work_groups"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'Orders' AND column_name = 'o_sample_name'
            ) THEN
                ALTER TABLE "public"."Orders" ADD COLUMN "o_sample_name" VARCHAR(255) NULL;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute('ALTER TABLE "public"."Orders" DROP COLUMN IF EXISTS "o_sample_name";')

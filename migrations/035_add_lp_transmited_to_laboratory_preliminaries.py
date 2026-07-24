"""
Migration 035: Add lp_transmited to LaboratoryPreliminaries.

Indica (0/1) si el resultado preliminar fue transmitido. Se marca en 0 cuando
el preliminar (o su laboratorio padre) se desvalida, para reflejar que ya
no está vigente y debe volver a transmitirse.

Safe to run even if the column already exists.
"""

from alembic import op
import sqlalchemy as sa

revision = "035_add_lp_transmited_to_laboratory_preliminaries"
down_revision = "034_drop_laboratories_l_order_detail_id_unique"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'LaboratoryPreliminaries'
                  AND column_name = 'lp_transmited'
            ) THEN
                ALTER TABLE "public"."LaboratoryPreliminaries"
                ADD COLUMN "lp_transmited" INTEGER NOT NULL DEFAULT 1;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE "public"."LaboratoryPreliminaries"
        DROP COLUMN IF EXISTS "lp_transmited";
    """)

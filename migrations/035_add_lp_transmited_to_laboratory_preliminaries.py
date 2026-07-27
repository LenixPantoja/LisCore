"""
Migration 035: Add lp_transmitted to LaboratoryPreliminaries.

Indica (0/1) si el resultado preliminar fue transmitido. Por defecto 0 (no
transmitido); se marca en 1 cuando se transmite, y vuelve a 0 cuando el
preliminar (o su laboratorio padre) se desvalida.

Safe to run even if the column already exists (también corrige el DEFAULT si
una ejecución previa lo dejó en 1).
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
                  AND column_name = 'lp_transmitted'
            ) THEN
                ALTER TABLE "public"."LaboratoryPreliminaries"
                ADD COLUMN "lp_transmitted" INTEGER NOT NULL DEFAULT 0;
            END IF;
        END
        $$;
    """)
    op.execute("""
        ALTER TABLE "public"."LaboratoryPreliminaries"
        ALTER COLUMN "lp_transmitted" SET DEFAULT 0;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE "public"."LaboratoryPreliminaries"
        DROP COLUMN IF EXISTS "lp_transmitted";
    """)

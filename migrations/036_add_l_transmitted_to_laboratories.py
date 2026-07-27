"""
Migration 036: Add l_transmitted to Laboratories.

Indica (0/1) si el resultado de laboratorio fue transmitido. Por defecto 0
(no transmitido); se marca en 1 cuando se transmite, y vuelve a 0 cuando el
laboratorio se desvalida.

Safe to run even if the column already exists (también corrige el DEFAULT si
una ejecución previa lo dejó en 1).
"""

from alembic import op
import sqlalchemy as sa

revision = "036_add_l_transmitted_to_laboratories"
down_revision = "035_add_lp_transmited_to_laboratory_preliminaries"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'Laboratories'
                  AND column_name = 'l_transmitted'
            ) THEN
                ALTER TABLE "public"."Laboratories"
                ADD COLUMN "l_transmitted" INTEGER NOT NULL DEFAULT 0;
            END IF;
        END
        $$;
    """)
    op.execute("""
        ALTER TABLE "public"."Laboratories"
        ALTER COLUMN "l_transmitted" SET DEFAULT 0;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE "public"."Laboratories"
        DROP COLUMN IF EXISTS "l_transmitted";
    """)

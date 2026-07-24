"""
Migration 036: Add l_transmitted to Laboratories.

Indica (0/1) si el resultado de laboratorio fue transmitido. Se marca en 0
cuando el laboratorio se desvalida, para reflejar que ya no está vigente y
debe volver a transmitirse.

Safe to run even if the column already exists.
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
                ADD COLUMN "l_transmitted" INTEGER NOT NULL DEFAULT 1;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE "public"."Laboratories"
        DROP COLUMN IF EXISTS "l_transmitted";
    """)

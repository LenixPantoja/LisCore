"""
Migration 040: Add g_discarted to Gradillas.

Indica (0/1) si la gradilla ya fue descartada. Por defecto 0 (no
descartada); se marca en 1 cuando se descarta la gradilla completa (ver
POST /api/seroteca/racks/{g_id}/discard), momento en el que también se
marcan todas sus muestras como Descartadas (SamplesOrder.so_state = 4).

Safe to run even if the column already exists.
"""

from alembic import op
import sqlalchemy as sa

revision = "040_add_g_discarted_to_gradillas"
down_revision = "039_add_ar_external_lab_id_to_annexed_result"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'Gradillas'
                  AND column_name = 'g_discarted'
            ) THEN
                ALTER TABLE "public"."Gradillas"
                ADD COLUMN "g_discarted" INTEGER NOT NULL DEFAULT 0;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE "public"."Gradillas"
        DROP COLUMN IF EXISTS "g_discarted";
    """)

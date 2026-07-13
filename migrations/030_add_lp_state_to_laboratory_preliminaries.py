"""
Migration 030: Add lp_state column to LaboratoryPreliminaries table.

States:
    0 - Pendiente
    1 - Validado
    2 - Desvalidado

Safe to run even if the column already exists.
"""

from alembic import op
import sqlalchemy as sa

revision = "030_add_lp_state_to_laboratory_preliminaries"
down_revision = "029_add_piso_to_inbound_orders"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'LaboratoryPreliminaries'
                  AND column_name = 'lp_state'
            ) THEN
                ALTER TABLE "public"."LaboratoryPreliminaries"
                ADD COLUMN "lp_state" INTEGER NOT NULL DEFAULT 0;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE "public"."LaboratoryPreliminaries"
        DROP COLUMN IF EXISTS "lp_state";
    """)
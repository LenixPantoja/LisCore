"""
Migration 042: Add g_work_group_id to Gradillas.

Permite asociar una gradilla a un grupo de trabajo (área de procesamiento).
Cuando está configurado, solo se pueden almacenar en esa gradilla muestras
que tengan estudios correspondientes a ese grupo de trabajo (ver
POST /api/seroteca/samples/store y /api/seroteca/positions/{gp_id}/store).
Nullable: una gradilla sin g_work_group_id no tiene esa restricción.

Safe to run even if the column already exists.
"""

from alembic import op
import sqlalchemy as sa

revision = "042_add_g_work_group_id_to_gradillas"
down_revision = "041_seed_seroteca_discard_permission"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'Gradillas'
                  AND column_name = 'g_work_group_id'
            ) THEN
                ALTER TABLE "public"."Gradillas"
                ADD COLUMN "g_work_group_id" INTEGER NULL
                REFERENCES "public"."Work_groups" ("wg_id") ON DELETE SET NULL;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE "public"."Gradillas"
        DROP COLUMN IF EXISTS "g_work_group_id";
    """)

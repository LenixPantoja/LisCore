"""
Migration 043: Replace Gradillas.g_work_group_id (single FK) with a
many-to-many table GradillaWorkGroups.

Una gradilla ahora puede estar asociada a VARIOS grupos de trabajo (áreas de
procesamiento) — se elige uno o más al crearla, y solo se pueden almacenar
en ella muestras cuyos estudios correspondan a alguno de esos grupos.

Pasos:
  1. Crea la tabla "GradillaWorkGroups" (gwg_gradilla_id, gwg_work_group_id).
  2. Migra los datos existentes de "Gradillas"."g_work_group_id" (si la
     columna existe) hacia la nueva tabla.
  3. Elimina la columna "Gradillas"."g_work_group_id".

Safe to run even if already applied.
"""

from alembic import op
import sqlalchemy as sa

revision = "043_gradilla_multiple_work_groups"
down_revision = "042_add_g_work_group_id_to_gradillas"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS "public"."GradillaWorkGroups" (
            "gwg_id" SERIAL PRIMARY KEY,
            "gwg_gradilla_id" INTEGER NOT NULL REFERENCES "public"."Gradillas" ("g_id") ON DELETE CASCADE,
            "gwg_work_group_id" INTEGER NOT NULL REFERENCES "public"."Work_groups" ("wg_id") ON DELETE CASCADE,
            CONSTRAINT "uq_gradilla_work_group" UNIQUE ("gwg_gradilla_id", "gwg_work_group_id")
        );
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'Gradillas' AND column_name = 'g_work_group_id'
            ) THEN
                INSERT INTO "public"."GradillaWorkGroups" ("gwg_gradilla_id", "gwg_work_group_id")
                SELECT "g_id", "g_work_group_id" FROM "public"."Gradillas"
                WHERE "g_work_group_id" IS NOT NULL
                ON CONFLICT DO NOTHING;

                ALTER TABLE "public"."Gradillas" DROP COLUMN "g_work_group_id";
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'Gradillas' AND column_name = 'g_work_group_id'
            ) THEN
                ALTER TABLE "public"."Gradillas"
                ADD COLUMN "g_work_group_id" INTEGER NULL
                REFERENCES "public"."Work_groups" ("wg_id") ON DELETE SET NULL;
            END IF;
        END
        $$;
    """)
    op.execute("""
        UPDATE "public"."Gradillas" g
        SET "g_work_group_id" = sub.wg_id
        FROM (
            SELECT DISTINCT ON (gwg_gradilla_id) gwg_gradilla_id, gwg_work_group_id AS wg_id
            FROM "public"."GradillaWorkGroups"
            ORDER BY gwg_gradilla_id, gwg_id
        ) sub
        WHERE g.g_id = sub.gwg_gradilla_id;
    """)
    op.execute('DROP TABLE IF EXISTS "public"."GradillaWorkGroups";')

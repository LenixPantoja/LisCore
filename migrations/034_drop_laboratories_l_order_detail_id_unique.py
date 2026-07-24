"""
Migration 034: Drop the UNIQUE constraint on Laboratories.l_order_detail_id.

OrdersDetails debe representar un estudio dentro de una orden (una fila por
estudio, no una fila por prueba). Con la restricción UNIQUE, un mismo od_id
solo podía tener UN Laboratory asociado, lo que obligaba a crear un
OrdersDetail distinto por cada prueba del estudio (duplicando od_study_id).

Al quitar la restricción, un mismo od_id puede tener varios resultados de
Laboratories asociados (uno por cada prueba del estudio), permitiendo que
OrdersDetails vuelva a representar "esta orden incluye este estudio".

Se conserva un índice simple (no único) sobre la columna para no perder
rendimiento en los JOIN existentes por od_id.

Safe to run even if the constraint doesn't exist (idempotent guard).
"""

from alembic import op
import sqlalchemy as sa

revision = "034_drop_laboratories_l_order_detail_id_unique"
down_revision = "033_create_app_results_page"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'Laboratories_l_order_detail_id_key'
            ) THEN
                ALTER TABLE "public"."Laboratories"
                DROP CONSTRAINT "Laboratories_l_order_detail_id_key";
            END IF;
        END
        $$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_laboratories_l_order_detail_id"
        ON "public"."Laboratories" ("l_order_detail_id");
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS "ix_laboratories_l_order_detail_id";
    """)
    op.execute("""
        ALTER TABLE "public"."Laboratories"
        ADD CONSTRAINT "Laboratories_l_order_detail_id_key" UNIQUE ("l_order_detail_id");
    """)

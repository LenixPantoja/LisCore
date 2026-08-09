"""
Migration 039: Add ar_external_lab_id to AnnexedResult.

Permite que un anexo (PDF) quede asociado a un laboratorio de referencia
externo específico (ExternalReferenceLaboratories.erl_id), para que la carga
de resultados anexos de una orden remitida sea por laboratorio: si una orden
tiene estudios remitidos a dos laboratorios distintos, cargar el PDF de uno
no debe afectar el estado del estudio remitido al otro.

Nullable porque los anexos genéricos (no ligados al flujo de remisiones)
no tienen laboratorio externo asociado.

Safe to run even if the column already exists.
"""

from alembic import op
import sqlalchemy as sa

revision = "039_add_ar_external_lab_id_to_annexed_result"
down_revision = "038_seed_remissions_annexed_permission"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'AnnexedResult'
                  AND column_name = 'ar_external_lab_id'
            ) THEN
                ALTER TABLE "public"."AnnexedResult"
                ADD COLUMN "ar_external_lab_id" INTEGER NULL
                REFERENCES "public"."ExternalReferenceLaboratories" ("erl_id");
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE "public"."AnnexedResult"
        DROP COLUMN IF EXISTS "ar_external_lab_id";
    """)

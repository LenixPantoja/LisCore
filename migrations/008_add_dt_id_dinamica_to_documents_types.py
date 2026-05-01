"""
Migration: Add dt_id_dinamica column to DocumentsTypes table.

Adds:
- DocumentsTypes.dt_id_dinamica (INTEGER, nullable): ID del tipo de documento
  en el sistema externo (HIS Dinamica). Usado para homologacion en la InterfazDG.

Safe to run even if the column already exists (uses ADD COLUMN IF NOT EXISTS).
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '008_add_dt_id_dinamica_to_documents_types'
down_revision = '007_create_invoices_and_invoices_detail_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE "public"."DocumentsTypes"
        ADD COLUMN IF NOT EXISTS "dt_id_dinamica" INTEGER NULL;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE "public"."DocumentsTypes"
        DROP COLUMN IF EXISTS "dt_id_dinamica";
    """)

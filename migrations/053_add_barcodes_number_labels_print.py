"""
Migration 053: Add number_labels_print to barcodes.

number_labels_print: cantidad de copias que se imprimen de cada etiqueta
generada con esa plantilla (por defecto 1).

Safe to run even if already applied.
"""

from alembic import op

revision = "053_add_barcodes_number_labels_print"
down_revision = "052_create_validation_notes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE "public"."barcodes"
        ADD COLUMN IF NOT EXISTS "number_labels_print" INTEGER NOT NULL DEFAULT 1;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_barcodes_number_labels_print'
            ) THEN
                ALTER TABLE "public"."barcodes"
                ADD CONSTRAINT "ck_barcodes_number_labels_print" CHECK ("number_labels_print" >= 1);
            END IF;
        END $$;
    """)


def downgrade():
    op.execute('ALTER TABLE "public"."barcodes" DROP CONSTRAINT IF EXISTS "ck_barcodes_number_labels_print";')
    op.execute('ALTER TABLE "public"."barcodes" DROP COLUMN IF EXISTS "number_labels_print";')

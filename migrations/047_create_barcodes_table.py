"""
Migration 047: Create barcodes table.

Guarda las plantillas ZPL de las etiquetas (muestras y gradillas) en la base
de datos en vez de quemarlas en el backend, para poder actualizarlas sin
recompilar la imagen Docker. label_type distingue la plantilla ('MUESTRA' o
'GRADILLA'); solo puede haber una fila activa (is_active=1) por label_type —
ver BarcodeRepository.get_active_template.

Safe to run even if already applied.
"""

from alembic import op
import sqlalchemy as sa

revision = "047_create_barcodes_table"
down_revision = "046_add_indexes_to_order_details_join_columns"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS "public"."barcodes" (
            id          SERIAL PRIMARY KEY,
            label_type  VARCHAR(20) NOT NULL,
            barcode     TEXT NOT NULL,
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_barcodes_label_type"
        ON "public"."barcodes" ("label_type");
    """)
    # Garantiza una sola plantilla activa por tipo de etiqueta
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS "ux_barcodes_active_type"
        ON "public"."barcodes" ("label_type")
        WHERE is_active = 1;
    """)


def downgrade():
    op.execute('DROP TABLE IF EXISTS "public"."barcodes";')

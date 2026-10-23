"""
Migration 052: Create validation_notes table.

Catálogo de notas predefinidas para la validación de resultados.
vn_active: 1 = activo, 0 = inactivo.

Safe to run even if already applied.
"""

from alembic import op

revision = "052_create_validation_notes"
down_revision = "051_add_headquarter_order_consecutive"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS "public"."validation_notes" (
            "vn_id"          SERIAL PRIMARY KEY,
            "vn_code"        VARCHAR(50)  NOT NULL,
            "vn_description" TEXT         NOT NULL,
            "vn_active"      INTEGER      NOT NULL DEFAULT 1,
            "vn_created_at"  TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Bogota'),
            "vn_updated_at"  TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Bogota'),
            CONSTRAINT "uq_validation_notes_code" UNIQUE ("vn_code"),
            CONSTRAINT "ck_validation_notes_active" CHECK ("vn_active" IN (0, 1))
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_validation_notes_active"
        ON "public"."validation_notes" ("vn_active");
    """)


def downgrade():
    op.execute('DROP TABLE IF EXISTS "public"."validation_notes";')

"""
Migration 050: Add AppUsers.usr_must_change_password.

Soporta el flujo de "clave temporal": al crear un usuario, la contraseña que
se le asigna queda marcada para forzar el cambio en el primer login. Default
false para no afectar usuarios ya existentes.

Safe to run even if already applied.
"""

from alembic import op
import sqlalchemy as sa

revision = "050_add_usr_must_change_password"
down_revision = "049_unique_index_inboundorders_number_request"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'AppUsers' AND column_name = 'usr_must_change_password'
            ) THEN
                ALTER TABLE "public"."AppUsers"
                ADD COLUMN "usr_must_change_password" BOOLEAN NOT NULL DEFAULT false;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute('ALTER TABLE "public"."AppUsers" DROP COLUMN IF EXISTS "usr_must_change_password";')

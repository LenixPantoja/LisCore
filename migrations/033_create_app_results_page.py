"""
Migration 033: Create AppResultsPage table.

Almacena los usuarios del portal de resultados (pacientes y empresas).
arp_user_origin_id apunta a Patients.pt_id o Enterprises.en_id según
arp_user_access_type (1 = Paciente, 2 = Empresa). La contraseña NO vive en
esta tabla: se gestiona directamente en Patients.pt_password /
Enterprises.en_password.
"""

from alembic import op
import sqlalchemy as sa

revision = "033_create_app_results_page"
down_revision = "032_backfill_null_lp_state"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "AppResultsPage",
        sa.Column("arp_user_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("arp_user_origin_id", sa.Integer, nullable=False),
        sa.Column("arp_user_login", sa.String(255), nullable=False),
        sa.Column("arp_user_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("arp_user_mail", sa.String(255), nullable=True),
        sa.Column("arp_user_access_type", sa.SmallInteger, nullable=False),
        sa.Column("arp_user_recovery", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("arp_last_access", sa.DateTime, nullable=True),
        sa.Column("arp_created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("arp_updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("arp_user_login", name="uq_app_results_page_login"),
        sa.UniqueConstraint("arp_user_origin_id", "arp_user_access_type", name="uq_app_results_page_origin"),
    )


def downgrade():
    op.drop_table("AppResultsPage")

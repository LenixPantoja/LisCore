"""
Migration: Seed Remissions:UploadAnnexedResult permission

Seeds the Permissions table with the permission used by the new endpoint
POST /api/remissions/orders/{order_id}/annexed-results, which uploads a PDF
for an order with remitted studies and marks its Laboratories as 'PDF ANEXO'.

Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "038_seed_remissions_annexed_permission"
down_revision = "037_add_lab_result_notify_trigger"
branch_labels = None
depends_on = None

_permissions_table = table(
    "Permissions",
    column("p_name", sa.String),
    column("p_description", sa.String),
    column("p_module", sa.String),
)

_PERMISSIONS = [
    {
        "p_name": "Remissions:UploadAnnexedResult",
        "p_description": "Cargar PDF anexo de una orden remitida y marcar sus pruebas como 'PDF ANEXO'",
        "p_module": "Remissions",
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    existing = {
        row[0]
        for row in conn.execute(sa.text('SELECT p_name FROM "Permissions"')).fetchall()
    }
    new_permissions = [p for p in _PERMISSIONS if p["p_name"] not in existing]
    if new_permissions:
        op.bulk_insert(_permissions_table, new_permissions)


def downgrade() -> None:
    conn = op.get_bind()
    names = [p["p_name"] for p in _PERMISSIONS]
    conn.execute(
        sa.text('DELETE FROM "Permissions" WHERE p_name = ANY(:names)'),
        {"names": names},
    )

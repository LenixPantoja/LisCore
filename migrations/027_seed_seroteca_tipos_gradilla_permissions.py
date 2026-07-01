"""
Migration: Seed Seroteca TipoGradilla permissions

Seeds permissions for the "Tipos de Gradilla" CRUD within the Seroteca module.

Permissions:
  Seroteca:ManageRackTypes

Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "027_seed_seroteca_tipos_gradilla_permissions"
down_revision = "026_create_tipos_gradilla_table"
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
        "p_name": "Seroteca:ManageRackTypes",
        "p_description": "Crear, editar, listar y eliminar tipos de gradilla (templates de racks)",
        "p_module": "Seroteca",
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
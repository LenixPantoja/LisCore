"""
Migration: Seed Remissions module permissions

Seeds the Permissions table with permissions for the Remissions module,
following the Module:Action naming convention.

Permissions:
  Remissions:View, Remissions:Create, Remissions:Ship, Remissions:Receive,
  Remissions:Cancel, Remissions:ManageExternalLabs

Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "022_seed_remissions_permissions"
down_revision = "021_create_annexed_result_table"
branch_labels = None
depends_on = None

_permissions_table = table(
    "Permissions",
    column("p_name", sa.String),
    column("p_description", sa.String),
    column("p_module", sa.String),
)

_PERMISSIONS = [
    {"p_name": "Remissions:View",              "p_description": "Ver y listar remisiones",                      "p_module": "Remissions"},
    {"p_name": "Remissions:Create",            "p_description": "Crear remisiones y agregar/quitar ítems",      "p_module": "Remissions"},
    {"p_name": "Remissions:Ship",              "p_description": "Enviar remisiones",                            "p_module": "Remissions"},
    {"p_name": "Remissions:Receive",           "p_description": "Procesar recepción de ítems en destino",       "p_module": "Remissions"},
    {"p_name": "Remissions:Cancel",            "p_description": "Cancelar remisiones pendientes",               "p_module": "Remissions"},
    {"p_name": "Remissions:ManageExternalLabs","p_description": "Crear, editar y eliminar laboratorios externos","p_module": "Remissions"},
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
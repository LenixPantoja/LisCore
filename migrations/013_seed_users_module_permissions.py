"""
Migration: Seed Users module permissions

Seeds the Permissions table with all permissions for the Users module
(AppUsers and Rols tables).

Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = '013_seed_users_module_permissions'
down_revision = '012_add_od_cancelled_to_orders_details'
branch_labels = None
depends_on = None

_permissions_table = table(
    "Permissions",
    column("p_name", sa.String),
    column("p_description", sa.String),
    column("p_module", sa.String),
)

_PERMISSIONS = [
    # AppUsers
    {
        "p_name": "AppUsers:All",
        "p_description": "Acceso completo",
        "p_module": "AppUsers",
    },
    {
        "p_name": "AppUsers:Create",
        "p_description": "Crear nuevos usuarios",
        "p_module": "AppUsers",
    },
    {
        "p_name": "AppUsers:Update",
        "p_description": "Actualizar datos de usuarios",
        "p_module": "AppUsers",
    },
    {
        "p_name": "AppUsers:List",
        "p_description": "Listar y consultar usuarios",
        "p_module": "AppUsers",
    },
    {
        "p_name": "AppUserPermissions:Vinculate",
        "p_description": "Asignar y revocar permisos a roles de usuario",
        "p_module": "AppUsers",
    },
    # Rols
    {
        "p_name": "Rols:All",
        "p_description": "Acceso completo al módulo de roles",
        "p_module": "Rols",
    },
    {
        "p_name": "Rols:Create",
        "p_description": "Crear nuevos roles",
        "p_module": "Rols",
    },
    {
        "p_name": "Rols:Update",
        "p_description": "Actualizar roles existentes",
        "p_module": "Rols",
    },
    {
        "p_name": "Rols:List",
        "p_description": "Listar y consultar roles",
        "p_module": "Rols",
    },
    {
        "p_name": "Rols:Delete",
        "p_description": "Eliminar roles",
        "p_module": "Rols",
    },
]


def upgrade() -> None:
    op.bulk_insert(_permissions_table, _PERMISSIONS)


def downgrade() -> None:
    conn = op.get_bind()
    names = [p["p_name"] for p in _PERMISSIONS]
    conn.execute(
        sa.text('DELETE FROM "Permissions" WHERE p_name = ANY(:names)'),
        {"names": names},
    )

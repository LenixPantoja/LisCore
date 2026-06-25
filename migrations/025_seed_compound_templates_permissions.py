"""
Migration: Seed CompoundTemplates module permissions

Seeds the Permissions table with permissions for the CompoundTemplates module,
following the Module:Action naming convention.

Permissions:
  CompoundTemplates:Create, CompoundTemplates:List, CompoundTemplates:GetOne,
  CompoundTemplates:Update, CompoundTemplates:Delete, CompoundTemplates:ManageLinks

Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "025_seed_compound_templates_permissions"
down_revision = "024_create_compound_templates_tables"
branch_labels = None
depends_on = None

_permissions_table = table(
    "Permissions",
    column("p_name", sa.String),
    column("p_description", sa.String),
    column("p_module", sa.String),
)

_PERMISSIONS = [
    {"p_name": "CompoundTemplates:Create",      "p_description": "Crear plantillas de completado dinámico",          "p_module": "CompoundTemplates"},
    {"p_name": "CompoundTemplates:List",         "p_description": "Listar y buscar plantillas",                       "p_module": "CompoundTemplates"},
    {"p_name": "CompoundTemplates:GetOne",       "p_description": "Ver detalle de una plantilla",                     "p_module": "CompoundTemplates"},
    {"p_name": "CompoundTemplates:Update",       "p_description": "Editar plantillas existentes",                     "p_module": "CompoundTemplates"},
    {"p_name": "CompoundTemplates:Delete",       "p_description": "Eliminar plantillas",                              "p_module": "CompoundTemplates"},
    {"p_name": "CompoundTemplates:ManageLinks",  "p_description": "Vincular/desvincular tests a plantillas",         "p_module": "CompoundTemplates"},
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
"""
Migration 041: Seed Seroteca:DiscardRack permission

Seeds the Permissions table with the permission used by the new endpoint
POST /api/seroteca/racks/{g_id}/discard, which discards a full rack and
all its stored samples.

Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "041_seed_seroteca_discard_permission"
down_revision = "040_add_g_discarted_to_gradillas"
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
        "p_name": "Seroteca:DiscardRack",
        "p_description": "Descartar una gradilla completa y sus muestras",
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

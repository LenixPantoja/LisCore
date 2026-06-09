"""
Migration: Add rp_active column to RolPermissions table

Adds a boolean column `rp_active` (default True) to the RolPermissions
intermediate table to allow soft-disabling role-permission assignments.
"""

from alembic import op
import sqlalchemy as sa

revision = '014_add_rp_active_to_rol_permissions'
down_revision = '013_seed_users_module_permissions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'RolPermissions',
        sa.Column('rp_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('RolPermissions', 'rp_active')

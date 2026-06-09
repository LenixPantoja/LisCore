"""
Migration 023: Add s_headquarter_id to Serotecas table.
"""

from alembic import op
import sqlalchemy as sa

revision = "023_add_headquarter_id_to_serotecas"
down_revision = "022_seed_remissions_permissions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "Serotecas",
        sa.Column("s_headquarter_id", sa.Integer, sa.ForeignKey("Headquarters.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade():
    op.drop_column("Serotecas", "s_headquarter_id")
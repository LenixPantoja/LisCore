"""
Migration 028: Add g_number and g_discard_date columns to Gradillas table.
"""

from alembic import op
import sqlalchemy as sa

revision = "028_add_gradilla_number_and_discard_date"
down_revision = "027_seed_seroteca_tipos_gradilla_permissions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "Gradillas",
        sa.Column("g_number", sa.String(50), nullable=True),
    )
    op.add_column(
        "Gradillas",
        sa.Column("g_discard_date", sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_column("Gradillas", "g_discard_date")
    op.drop_column("Gradillas", "g_number")
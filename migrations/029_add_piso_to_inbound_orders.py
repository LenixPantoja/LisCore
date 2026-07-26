"""
Migration 029: Add io_Piso column to InboundOrders table.
"""

from alembic import op
import sqlalchemy as sa

revision = "029_add_piso_to_inbound_orders"
down_revision = "028_add_gradilla_number_and_discard_date"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "InboundOrders",
        sa.Column("io_Piso", sa.String(500), nullable=True),
    )


def downgrade():
    op.drop_column("InboundOrders", "io_Piso")
"""
Migration 048: Add index to Orders.o_headquarter_id.

POST /api/orders/filter ahora acepta headquarter_ids para filtrar por sede
(Order.o_headquarter_id), igual que ya filtra por o_created_at/o_order_state
(ver migración 045). Sin índice, ese filtro haría table scan sobre Orders.

Safe to run even if already applied.
"""

from alembic import op
import sqlalchemy as sa

revision = "048_add_index_orders_headquarter_id"
down_revision = "047_create_barcodes_table"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_orders_o_headquarter_id"
        ON "public"."Orders" ("o_headquarter_id");
    """)


def downgrade():
    op.execute('DROP INDEX IF EXISTS "ix_orders_o_headquarter_id";')

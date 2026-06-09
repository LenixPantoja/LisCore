"""
Migration: Add od_cancelled column to OrdersDetails table.

Adds:
- OrdersDetails.od_cancelled (INTEGER, NOT NULL, DEFAULT 0): 1 when the study is cancelled.

Safe to run even if the column already exists (uses ADD COLUMN IF NOT EXISTS).
"""

from alembic import op

revision = '012_add_od_cancelled_to_orders_details'
down_revision = '011_add_cancelled_fields_to_orders'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE "public"."OrdersDetails"
        ADD COLUMN IF NOT EXISTS "od_cancelled" INTEGER NOT NULL DEFAULT 0;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE "public"."OrdersDetails"
        DROP COLUMN IF EXISTS "od_cancelled";
    """)

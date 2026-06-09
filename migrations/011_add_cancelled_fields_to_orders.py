"""
Migration: Add o_cancelled to Orders and od_cancelled to OrdersDetails.

Adds:
- Orders.o_cancelled (INTEGER, NOT NULL, DEFAULT 0): 1 when all studies are cancelled.
- OrdersDetails.od_cancelled (INTEGER, NOT NULL, DEFAULT 0): 1 when a specific study is cancelled.

Safe to run even if the columns already exist (uses ADD COLUMN IF NOT EXISTS).
"""

from alembic import op

revision = '011_add_cancelled_fields_to_orders'
down_revision = '010_add_formula_fields_to_testslab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE "public"."Orders"
        ADD COLUMN IF NOT EXISTS "o_cancelled" INTEGER NOT NULL DEFAULT 0;
    """)
    op.execute("""
        ALTER TABLE "public"."OrdersDetails"
        ADD COLUMN IF NOT EXISTS "od_cancelled" INTEGER NOT NULL DEFAULT 0;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE "public"."Orders"
        DROP COLUMN IF EXISTS "o_cancelled";
    """)
    op.execute("""
        ALTER TABLE "public"."OrdersDetails"
        DROP COLUMN IF EXISTS "od_cancelled";
    """)

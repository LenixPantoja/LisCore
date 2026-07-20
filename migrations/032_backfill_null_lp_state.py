"""
Migration 032: Backfill NULL lp_state values on LaboratoryPreliminaries and
enforce the NOT NULL constraint.

Migration 030 added lp_state as NOT NULL DEFAULT 0, but some environments
ended up with NULL values in existing rows (e.g. rows inserted directly
without going through the ORM default), which breaks response validation
on GET /api/orders/{id}/full (lp_state expected as int, got None).

Safe to run multiple times.
"""

from alembic import op
import sqlalchemy as sa

revision = "032_backfill_null_lp_state"
down_revision = "031_add_service_code_name_to_inbound_orders"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE "public"."LaboratoryPreliminaries"
        SET "lp_state" = 0
        WHERE "lp_state" IS NULL;
    """)
    op.execute("""
        ALTER TABLE "public"."LaboratoryPreliminaries"
        ALTER COLUMN "lp_state" SET NOT NULL;
    """)
    op.execute("""
        ALTER TABLE "public"."LaboratoryPreliminaries"
        ALTER COLUMN "lp_state" SET DEFAULT 0;
    """)


def downgrade():
    pass

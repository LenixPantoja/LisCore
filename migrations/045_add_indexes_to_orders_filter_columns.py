"""
Migration 045: Add indexes to speed up POST /api/orders/filter.

Orders.o_created_at y Orders.o_order_state se usan como filtros principales
(rango de fecha/hora y estado) y no tenian indice, forzando un table scan
completo sobre Orders. OrdersDetails.od_order_id y od_study_id se usan en
el JOIN hacia OrdersDetails/StudiesLab al filtrar por work_group_ids o
study_ids, y tampoco tenian indice (Postgres no indexa FKs automaticamente).

Safe to run even if already applied.
"""

from alembic import op
import sqlalchemy as sa

revision = "045_add_indexes_to_orders_filter_columns"
down_revision = "044_add_o_sample_name_to_orders"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_orders_o_created_at"
        ON "public"."Orders" ("o_created_at");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_orders_o_order_state"
        ON "public"."Orders" ("o_order_state");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_ordersdetails_od_order_id"
        ON "public"."OrdersDetails" ("od_order_id");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_ordersdetails_od_study_id"
        ON "public"."OrdersDetails" ("od_study_id");
    """)


def downgrade():
    op.execute('DROP INDEX IF EXISTS "ix_orders_o_created_at";')
    op.execute('DROP INDEX IF EXISTS "ix_orders_o_order_state";')
    op.execute('DROP INDEX IF EXISTS "ix_ordersdetails_od_order_id";')
    op.execute('DROP INDEX IF EXISTS "ix_ordersdetails_od_study_id";')

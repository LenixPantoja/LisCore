"""
Migration 051: Consecutivo de órdenes por sede.

- Headquarters.order_consecutive_next: próximo consecutivo a asignar en la sede
  (1..999999999). Arranca en 1 para todas las sedes.
- Orders.o_hq_consecutive: consecutivo asignado a la orden dentro de su sede.
  NULL para órdenes anteriores a esta migración o sin sede.
- Índice único (o_headquarter_id, o_hq_consecutive) como respaldo contra
  duplicados.

Safe to run even if already applied.
"""

from alembic import op

revision = "051_add_headquarter_order_consecutive"
down_revision = "050_add_usr_must_change_password"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'Headquarters' AND column_name = 'order_consecutive_next'
            ) THEN
                ALTER TABLE "public"."Headquarters"
                ADD COLUMN "order_consecutive_next" INTEGER NOT NULL DEFAULT 1;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'Orders' AND column_name = 'o_hq_consecutive'
            ) THEN
                ALTER TABLE "public"."Orders"
                ADD COLUMN "o_hq_consecutive" INTEGER NULL;
            END IF;
        END
        $$;
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS "uq_orders_hq_consecutive"
        ON "public"."Orders" ("o_headquarter_id", "o_hq_consecutive")
        WHERE "o_hq_consecutive" IS NOT NULL;
    """)


def downgrade():
    op.execute('DROP INDEX IF EXISTS "public"."uq_orders_hq_consecutive";')
    op.execute('ALTER TABLE "public"."Orders" DROP COLUMN IF EXISTS "o_hq_consecutive";')
    op.execute('ALTER TABLE "public"."Headquarters" DROP COLUMN IF EXISTS "order_consecutive_next";')

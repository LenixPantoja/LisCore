"""
Migration 037: Trigger de notificación para resultados de laboratorio.

Cuando una interfaz externa (analizador / motor de transmisión) escribe
l_result o l_result_num directamente en la base de datos —sin pasar por la
API de este backend—, las pruebas calculadas por fórmula que dependen de ese
resultado no se recalculaban, porque el recálculo solo se disparaba desde
LaboratoryRepository.bulk_update.

Este trigger emite un pg_notify('lab_result_changed', order_id) cada vez que
se inserta/actualiza l_result o l_result_num en una prueba que NO es de
fórmula (para evitar que el propio recálculo se dispare a sí mismo en bucle).
El backend escucha ese canal (ver
app/domains/laboratories/infrastructure/formula_listener.py) y recalcula las
fórmulas de esa orden.

Safe to run multiple times (usa CREATE OR REPLACE / DROP ... IF EXISTS).
"""

from alembic import op
import sqlalchemy as sa

revision = "037_add_lab_result_notify_trigger"
down_revision = "036_add_l_transmitted_to_laboratories"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_lab_result_change() RETURNS trigger AS $$
        DECLARE
            v_order_id INTEGER;
            v_is_formula BOOLEAN;
        BEGIN
            IF TG_OP = 'UPDATE'
               AND NEW.l_result IS NOT DISTINCT FROM OLD.l_result
               AND NEW.l_result_num IS NOT DISTINCT FROM OLD.l_result_num THEN
                RETURN NEW;
            END IF;

            SELECT is_formula INTO v_is_formula FROM "TestsLab" WHERE id = NEW.l_test_id;
            IF v_is_formula IS TRUE THEN
                -- Evita que el propio recálculo de fórmulas dispare otra notificación.
                RETURN NEW;
            END IF;

            SELECT od_order_id INTO v_order_id
            FROM "OrdersDetails"
            WHERE od_id = NEW.l_order_detail_id;

            IF v_order_id IS NOT NULL THEN
                PERFORM pg_notify('lab_result_changed', v_order_id::text);
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_notify_lab_result_change ON "Laboratories";
    """)
    op.execute("""
        CREATE TRIGGER trg_notify_lab_result_change
        AFTER INSERT OR UPDATE OF l_result, l_result_num ON "Laboratories"
        FOR EACH ROW
        EXECUTE FUNCTION notify_lab_result_change();
    """)


def downgrade():
    op.execute('DROP TRIGGER IF EXISTS trg_notify_lab_result_change ON "Laboratories";')
    op.execute('DROP FUNCTION IF EXISTS notify_lab_result_change();')

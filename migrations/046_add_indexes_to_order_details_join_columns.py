"""
Migration 046: Add indexes to speed up GET /api/orders/by-number/{o_number}/details.

Ese endpoint arma la respuesta con varios JOINs/batch-queries hacia tablas de
catalogo (StudiesTestDetail, RangesReferences, ReferencesValues,
TestslabFormatComplete) y hacia Laboratories.l_test_id, ninguna de las cuales
tenia indice en sus columnas FK (Postgres no indexa FKs automaticamente). Con
esas tablas creciendo, cada consulta batch (IN (...)) termina escaneando la
tabla completa aunque la lista de IDs sea pequena (los tests/estudios de una
sola orden).

Safe to run even if already applied.
"""

from alembic import op
import sqlalchemy as sa

revision = "046_add_indexes_to_order_details_join_columns"
down_revision = "045_add_indexes_to_orders_filter_columns"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_studiestestdetail_studies_id"
        ON "public"."StudiesTestDetail" ("studies_id");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_studiestestdetail_tests_id"
        ON "public"."StudiesTestDetail" ("tests_id");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_rangesreferences_test_id"
        ON "public"."RangesReferences" ("test_id");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_referencesvalues_ranges_references_id"
        ON "public"."ReferencesValues" ("ranges_references_id");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_testslabformatcomplete_tfc_testslab_id"
        ON "public"."TestslabFormatComplete" ("tfc_testslab_id");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_laboratories_l_test_id"
        ON "public"."Laboratories" ("l_test_id");
    """)


def downgrade():
    op.execute('DROP INDEX IF EXISTS "ix_studiestestdetail_studies_id";')
    op.execute('DROP INDEX IF EXISTS "ix_studiestestdetail_tests_id";')
    op.execute('DROP INDEX IF EXISTS "ix_rangesreferences_test_id";')
    op.execute('DROP INDEX IF EXISTS "ix_referencesvalues_ranges_references_id";')
    op.execute('DROP INDEX IF EXISTS "ix_testslabformatcomplete_tfc_testslab_id";')
    op.execute('DROP INDEX IF EXISTS "ix_laboratories_l_test_id";')

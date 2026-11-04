"""
Migration 058: Hojas de trabajo (WorkSheets, WorkSheetStudies) y sus permisos.

Ejecuta migrations/sql/058_hojas_de_trabajo.sql (idempotente).
"""

from pathlib import Path

from alembic import op

revision = "058_create_worksheets"
down_revision = "054_add_missing_production_indexes"
branch_labels = None
depends_on = None


def upgrade():
    sql = (Path(__file__).parent / "sql" / "058_hojas_de_trabajo.sql").read_text(encoding="utf-8")
    # La última consulta del script es solo de verificación
    op.execute(sql.split("-- Verificación")[0])


def downgrade():
    op.execute('DROP TABLE IF EXISTS "WorkSheetStudies";')
    op.execute('DROP TABLE IF EXISTS "WorkSheets";')
    op.execute("""
        DELETE FROM "RolPermissions" WHERE rp_permission_id IN
            (SELECT p_id FROM "Permissions" WHERE p_module = 'WorkSheets');
        DELETE FROM "Permissions" WHERE p_module = 'WorkSheets';
    """)

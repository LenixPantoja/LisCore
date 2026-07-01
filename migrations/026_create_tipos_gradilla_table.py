"""
Migration 026: Create TiposGradilla table and add g_tipo_gradilla_id FK to Gradillas.
"""

from alembic import op
import sqlalchemy as sa

revision = "026_create_tipos_gradilla_table"
down_revision = "025_seed_compound_templates_permissions"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create TiposGradilla table
    op.create_table(
        "TiposGradilla",
        sa.Column("tg_id", sa.Integer, primary_key=True, index=True, autoincrement=True),
        sa.Column("tg_name", sa.String(255), nullable=False),
        sa.Column("tg_rows", sa.Integer, nullable=False),
        sa.Column("tg_cols", sa.Integer, nullable=False),
        sa.Column("tg_storage_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("tg_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("tg_created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("tg_updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 2. Add g_tipo_gradilla_id FK column to Gradillas
    op.add_column(
        "Gradillas",
        sa.Column("g_tipo_gradilla_id", sa.Integer, sa.ForeignKey("TiposGradilla.tg_id", ondelete="SET NULL"), nullable=True),
    )


def downgrade():
    op.drop_column("Gradillas", "g_tipo_gradilla_id")
    op.drop_table("TiposGradilla")
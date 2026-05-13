"""
Migration 016: Create seroteca and sample tracking tables.

Note: SamplesLog already exists in the database - only new tables are created.

New tables:
  - Serotecas        - physical storage units
  - Gradillas        - racks inside a seroteca (user-defined rows x cols)
  - GradillaPosiciones - individual positions auto-generated per rack
"""

from alembic import op
import sqlalchemy as sa

revision = "016_create_seroteca_tracking_tables"
down_revision = "015_seed_all_modules_permissions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "Serotecas",
        sa.Column("s_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("s_name", sa.String(255), nullable=False),
        sa.Column("s_description", sa.Text, nullable=True),
        sa.Column("s_location_id", sa.Integer, sa.ForeignKey("locations.loc_id", ondelete="SET NULL"), nullable=True),
        sa.Column("s_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("s_created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("s_updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "Gradillas",
        sa.Column("g_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("g_name", sa.String(255), nullable=False),
        sa.Column("g_seroteca_id", sa.Integer, sa.ForeignKey("Serotecas.s_id", ondelete="CASCADE"), nullable=False),
        sa.Column("g_rows", sa.Integer, nullable=False),
        sa.Column("g_cols", sa.Integer, nullable=False),
        sa.Column("g_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("g_created_by", sa.Integer, sa.ForeignKey("AppUsers.usr_id", ondelete="SET NULL"), nullable=True),
        sa.Column("g_created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("g_updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "GradillaPosiciones",
        sa.Column("gp_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("gp_gradilla_id", sa.Integer, sa.ForeignKey("Gradillas.g_id", ondelete="CASCADE"), nullable=False),
        sa.Column("gp_row", sa.Integer, nullable=False),
        sa.Column("gp_col", sa.Integer, nullable=False),
        sa.Column("gp_sample_id", sa.Integer, sa.ForeignKey("SamplesOrder.so_id", ondelete="SET NULL"), nullable=True),
        sa.Column("gp_occupied", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("gp_stored_at", sa.DateTime, nullable=True),
        sa.Column("gp_stored_by_id", sa.Integer, sa.ForeignKey("AppUsers.usr_id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("gp_gradilla_id", "gp_row", "gp_col", name="uq_gradilla_posicion"),
    )


def downgrade():
    op.drop_table("GradillaPosiciones")
    op.drop_table("Gradillas")
    op.drop_table("Serotecas")

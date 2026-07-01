"""
Migration: Create CompoundTemplates and TestCompoundTemplates tables.

CompoundTemplates: stores dynamic result templates (JSONB).
TestCompoundTemplates: N:M pivot between TestsLab and CompoundTemplates.

Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "024_create_compound_templates_tables"
down_revision = "023_add_headquarter_id_to_serotecas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "CompoundTemplates",
        sa.Column("ct_id", sa.Integer, primary_key=True, index=True),
        sa.Column("ct_name", sa.String(255), nullable=False),
        sa.Column("ct_description", sa.Text, nullable=True),
        sa.Column("ct_template", JSONB, nullable=False, server_default=sa.text("'{\"template\": []}'::jsonb")),
        sa.Column("ct_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("ct_created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("ct_updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "TestCompoundTemplates",
        sa.Column("tct_id", sa.Integer, primary_key=True, index=True),
        sa.Column("tct_test_id", sa.Integer, sa.ForeignKey("TestsLab.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tct_template_id", sa.Integer, sa.ForeignKey("CompoundTemplates.ct_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tct_is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("tct_order_index", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("tct_created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Unique constraint: un test solo puede estar vinculado una vez a una misma plantilla
    op.create_unique_constraint(
        "uq_TestCompoundTemplates_test_template",
        "TestCompoundTemplates",
        ["tct_test_id", "tct_template_id"],
    )


def downgrade() -> None:
    op.drop_table("TestCompoundTemplates")
    op.drop_table("CompoundTemplates")
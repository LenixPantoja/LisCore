"""
Migration 018: Add dr_category_name to DynamicReports.

Allows grouping reports into named categories for tree-style listing.
"""

from alembic import op
import sqlalchemy as sa

revision = "018_add_category_to_dynamic_reports"
down_revision = "017_create_dynamic_reports_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "DynamicReports",
        sa.Column("dr_category_name", sa.String(150), nullable=True),
    )
    op.create_index(
        "ix_dynamic_reports_category_name",
        "DynamicReports",
        ["dr_category_name"],
    )


def downgrade():
    op.drop_index("ix_dynamic_reports_category_name", table_name="DynamicReports")
    op.drop_column("DynamicReports", "dr_category_name")

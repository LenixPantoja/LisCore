"""
Migration 017: Create dynamic reports tables.

New tables:
  - DynamicReports      — stores report definition: name, SQL query, HTML template
  - ReportParameters    — stores filter parameters per report (date, select, text, etc.)
"""

from alembic import op
import sqlalchemy as sa

revision = "017_create_dynamic_reports_tables"
down_revision = "016_create_seroteca_tracking_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "DynamicReports",
        sa.Column("dr_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("dr_name", sa.String(200), nullable=False),
        sa.Column("dr_description", sa.Text, nullable=True),
        sa.Column("dr_sql_query", sa.Text, nullable=False),
        sa.Column("dr_html_template", sa.Text, nullable=False),
        sa.Column("dr_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("dr_created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("dr_updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "ReportParameters",
        sa.Column("rp_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "rp_report_id",
            sa.Integer,
            sa.ForeignKey("DynamicReports.dr_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rp_name", sa.String(100), nullable=False),
        sa.Column("rp_label", sa.String(100), nullable=False),
        # Allowed: date | datetime | text | number | select | multiselect | checkbox | textarea
        sa.Column("rp_type", sa.String(50), nullable=False),
        sa.Column("rp_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("rp_default_value", sa.Text, nullable=True),
        sa.Column("rp_source_query", sa.Text, nullable=True),
        sa.Column("rp_order_index", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_index("ix_report_parameters_report_id", "ReportParameters", ["rp_report_id"])


def downgrade():
    op.drop_index("ix_report_parameters_report_id", table_name="ReportParameters")
    op.drop_table("ReportParameters")
    op.drop_table("DynamicReports")

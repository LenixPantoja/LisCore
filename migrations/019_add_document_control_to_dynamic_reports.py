"""
Migration 019: Add document control fields to DynamicReports.

New columns:
  - dr_code           — document code shown in the PDF header (e.g. F-OS007)
  - dr_version        — document version shown in the PDF header (e.g. 03)
  - dr_emission_date  — emission date shown in the PDF header (e.g. 13/09/2023)
"""

from alembic import op
import sqlalchemy as sa

revision = "019_add_document_control_to_dynamic_reports"
down_revision = "018_add_category_to_dynamic_reports"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("DynamicReports", sa.Column("dr_code", sa.String(50), nullable=True))
    op.add_column("DynamicReports", sa.Column("dr_version", sa.String(20), nullable=True))
    op.add_column("DynamicReports", sa.Column("dr_emission_date", sa.String(20), nullable=True))


def downgrade():
    op.drop_column("DynamicReports", "dr_emission_date")
    op.drop_column("DynamicReports", "dr_version")
    op.drop_column("DynamicReports", "dr_code")

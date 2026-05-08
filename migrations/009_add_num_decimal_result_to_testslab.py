"""
Migration: Add num_decimal_result column to TestsLab table

Adds a nullable INTEGER column to control the number of decimal places
displayed for numeric results (test_type = 'N') in l_result and l_result_num.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '009_add_num_decimal_result_to_testslab'
down_revision = '008_add_dt_id_dinamica_to_documents_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'TestsLab',
        sa.Column('num_decimal_result', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('TestsLab', 'num_decimal_result')

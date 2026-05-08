"""
Migration: Add alternative_range_value column to TestsLab table

Adds a nullable TEXT column to store alternative reference ranges for a test.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '002_add_alternative_range_value_to_testslab'
down_revision = '001_add_unique_constraint_contract_tariff'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'TestsLab',
        sa.Column('alternative_range_value', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('TestsLab', 'alternative_range_value')

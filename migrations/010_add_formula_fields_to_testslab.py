"""
Migration: Add is_formula and formula columns to TestsLab table

is_formula (Boolean, default False) indicates whether the test result
is computed from a formula instead of being entered manually.
formula (String 500) stores the expression string to be evaluated.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '010_add_formula_fields_to_testslab'
down_revision = '009_add_num_decimal_result_to_testslab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'TestsLab',
        sa.Column('is_formula', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'TestsLab',
        sa.Column('formula', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('TestsLab', 'formula')
    op.drop_column('TestsLab', 'is_formula')

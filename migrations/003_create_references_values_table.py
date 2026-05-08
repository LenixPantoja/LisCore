"""
Migration: Create ReferencesValues table

Creates the ReferencesValues table linked to TestsLab via rf_test_id.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '003_create_references_values_table'
down_revision = '002_add_alternative_range_value_to_testslab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ReferencesValues',
        sa.Column('rf_id', sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column('rf_test_id', sa.Integer(), sa.ForeignKey('TestsLab.id'), nullable=True),
        sa.Column('rf_sex_type', sa.String(255), nullable=True),
        sa.Column('rf_min_age_hours', sa.Integer(), nullable=True),
        sa.Column('rf_max_age_hours', sa.Integer(), nullable=True),
        sa.Column('rf_type', sa.String(50), nullable=True),
        sa.Column('rf_min_value', sa.Numeric(), nullable=True),
        sa.Column('rf_max_values', sa.Numeric(), nullable=True),
        sa.Column('rf_text_value', sa.Text(), nullable=True),
        sa.Column('rf_created_at', sa.DateTime(), nullable=True),
        sa.Column('rf_updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index(
        'ix_ReferencesValues_rf_test_id',
        'ReferencesValues',
        ['rf_test_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_ReferencesValues_rf_test_id', table_name='ReferencesValues')
    op.drop_table('ReferencesValues')

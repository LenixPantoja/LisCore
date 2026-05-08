"""
Migration: Restructure reference values into RangesReferences and ReferencesValues tables.

Drops the old ReferencesValues table (single-table design) and creates two normalized tables:
- RangesReferences: stores range metadata (type, gender, age range, priority) linked to TestsLab.
- ReferencesValues: stores the actual numeric/text values linked to RangesReferences.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '006_restructure_ranges_and_reference_values'
down_revision = '005_add_rf_units_display_to_references_values'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old ReferencesValues table
    op.drop_index('ix_ReferencesValues_rf_test_id', table_name='ReferencesValues', if_exists=True)
    op.drop_table('ReferencesValues')

    # Drop the old sequence if it exists
    op.execute("DROP SEQUENCE IF EXISTS references_values_rf_id_seq")

    # Create RangesReferences table
    op.create_table(
        'RangesReferences',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('range_type', sa.String(50), nullable=True),
        sa.Column('test_id', sa.Integer(), sa.ForeignKey('TestsLab.id'), nullable=True),
        sa.Column('gender', sa.String(10), nullable=True),
        sa.Column('age_type', sa.String(10), nullable=True),
        sa.Column('min_age', sa.Integer(), nullable=True),
        sa.Column('max_age', sa.Integer(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_RangesReferences_test_id', 'RangesReferences', ['test_id'])

    # Create ReferencesValues table (linked to RangesReferences)
    op.create_table(
        'ReferencesValues',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('ranges_references_id', sa.Integer(), sa.ForeignKey('RangesReferences.id'), nullable=True),
        sa.Column('min_value', sa.Numeric(), nullable=True),
        sa.Column('max_values', sa.Numeric(), nullable=True),
        sa.Column('text_value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_ReferencesValues_ranges_references_id', 'ReferencesValues', ['ranges_references_id'])


def downgrade() -> None:
    op.drop_index('ix_ReferencesValues_ranges_references_id', table_name='ReferencesValues', if_exists=True)
    op.drop_table('ReferencesValues')
    op.drop_index('ix_RangesReferences_test_id', table_name='RangesReferences', if_exists=True)
    op.drop_table('RangesReferences')

    # Recreate the old ReferencesValues table
    op.execute("CREATE SEQUENCE IF NOT EXISTS references_values_rf_id_seq")
    op.create_table(
        'ReferencesValues',
        sa.Column('rf_id', sa.BigInteger(), primary_key=True, nullable=False,
                  server_default=sa.text("nextval('references_values_rf_id_seq')")),
        sa.Column('rf_test_id', sa.Integer(), sa.ForeignKey('TestsLab.id'), nullable=True),
        sa.Column('rf_sextype', sa.String(255), nullable=True),
        sa.Column('rf_min_age_hours', sa.Integer(), nullable=True),
        sa.Column('rf_max_age_hours', sa.Integer(), nullable=True),
        sa.Column('rf_type', sa.String(50), nullable=True),
        sa.Column('rf_min_value', sa.Numeric(), nullable=True),
        sa.Column('rf_max_values', sa.Numeric(), nullable=True),
        sa.Column('rf_text_value', sa.Text(), nullable=True),
        sa.Column('rf_units_display', sa.Text(), nullable=True),
        sa.Column('rf_created_at', sa.DateTime(), nullable=True),
        sa.Column('rf_updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_ReferencesValues_rf_test_id', 'ReferencesValues', ['rf_test_id'])

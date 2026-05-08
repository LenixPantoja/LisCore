"""
Migration: Add rf_units_display column to ReferencesValues table
"""

from alembic import op
import sqlalchemy as sa

revision = '005_add_rf_units_display_to_references_values'
down_revision = '004_add_sequence_to_references_values_rf_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'ReferencesValues',
        sa.Column('rf_units_display', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('ReferencesValues', 'rf_units_display')

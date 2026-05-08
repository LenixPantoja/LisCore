"""
Migration: Add auto-increment sequence to ReferencesValues.rf_id

The rf_id column was created as plain bigint without a sequence.
This migration creates the sequence and sets it as the column default.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '004_add_sequence_to_references_values_rf_id'
down_revision = '003_create_references_values_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS references_values_rf_id_seq")
    op.execute(
        "ALTER TABLE \"ReferencesValues\" "
        "ALTER COLUMN rf_id SET DEFAULT nextval('references_values_rf_id_seq')"
    )
    op.execute(
        "ALTER SEQUENCE references_values_rf_id_seq OWNED BY \"ReferencesValues\".rf_id"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE \"ReferencesValues\" ALTER COLUMN rf_id DROP DEFAULT"
    )
    op.execute("DROP SEQUENCE IF EXISTS references_values_rf_id_seq")

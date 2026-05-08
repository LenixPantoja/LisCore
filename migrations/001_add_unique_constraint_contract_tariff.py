"""
Migration: Add unique constraint to ContractsTariffs table

This migration adds a unique constraint on (ct_contract_id, ct_tariff_id) 
to prevent duplicate tariff-contract links at the database level.

Run this with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '001_add_unique_constraint_contract_tariff'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraint to prevent duplicate contract-tariff links"""
    op.create_unique_constraint(
        'uq_contract_tariff',
        'ContractsTariffs',
        ['ct_contract_id', 'ct_tariff_id']
    )


def downgrade() -> None:
    """Remove unique constraint"""
    op.drop_constraint(
        'uq_contract_tariff',
        'ContractsTariffs',
        type_='unique'
    )

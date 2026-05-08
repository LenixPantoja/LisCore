"""
Migration: Create Invoices and InvoicesDetail tables for the billing domain.

Creates:
- Invoices: invoice header with FK to Enterprises, Patients, ContractsTariffs and AppUsers.
- InvoicesDetail: invoice line items with FK to Invoices, OrdersDetails, StudiesLab and AppUsers.

Safe to run even if the tables already exist (uses IF NOT EXISTS and ADD COLUMN IF NOT EXISTS).
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '007_create_invoices_and_invoices_detail_tables'
down_revision = '006_restructure_ranges_and_reference_values'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create Invoices table (safe: IF NOT EXISTS)
    op.execute("""
        CREATE TABLE IF NOT EXISTS "public"."Invoices" (
            "inv_id"          SERIAL       NOT NULL,
            "inv_number"      VARCHAR(255),
            "inv_date"        DATE,
            "inv_due_date"    DATE,
            "inv_enterprise_id" INT,
            "inv_patient_id"  INT,
            "inv_contract_id" INT,
            "inv_subtotal"    NUMERIC,
            "inv_tax"         NUMERIC,
            "inv_total"       NUMERIC,
            "inv_state"       INT,
            "inv_type"        INT,
            "inv_notes"       TEXT,
            "inv_created_by"  INT,
            "inv_created_at"  DATE,
            "inv_updated_at"  DATE,
            "tariff_id"       BIGINT,
            PRIMARY KEY ("inv_id")
        );
    """)

    # Add tariff_id column if the table existed without it
    op.execute("""
        ALTER TABLE "public"."Invoices"
        ADD COLUMN IF NOT EXISTS "tariff_id" BIGINT;
    """)

    # Add FK constraints if they don't already exist (catch errors silently)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_invoices_enterprise'
            ) THEN
                ALTER TABLE "public"."Invoices"
                ADD CONSTRAINT fk_invoices_enterprise
                FOREIGN KEY (inv_enterprise_id) REFERENCES "Enterprises"(en_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_invoices_patient'
            ) THEN
                ALTER TABLE "public"."Invoices"
                ADD CONSTRAINT fk_invoices_patient
                FOREIGN KEY (inv_patient_id) REFERENCES "Patients"(pt_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_invoices_contract'
            ) THEN
                ALTER TABLE "public"."Invoices"
                ADD CONSTRAINT fk_invoices_contract
                FOREIGN KEY (inv_contract_id) REFERENCES "ContractsTariffs"(ct_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_invoices_created_by'
            ) THEN
                ALTER TABLE "public"."Invoices"
                ADD CONSTRAINT fk_invoices_created_by
                FOREIGN KEY (inv_created_by) REFERENCES "AppUsers"(usr_id);
            END IF;
        END
        $$;
    """)

    op.execute('CREATE INDEX IF NOT EXISTS "ix_Invoices_inv_number" ON "public"."Invoices" (inv_number);')

    # Create InvoicesDetail table (safe: IF NOT EXISTS)
    op.execute("""
        CREATE TABLE IF NOT EXISTS "public"."InvoicesDetail" (
            "invd_id"              SERIAL    NOT NULL,
            "invd_invoice_id"      INT,
            "invd_order_detail_id" INT,
            "invd_study_id"        INT,
            "invd_value"           NUMERIC,
            "invd_discount"        NUMERIC,
            "invd_total"           NUMERIC,
            "invd_created_by"      INT,
            "invd_created_at"      TIMESTAMP,
            "invd_updated_at"      TIMESTAMP,
            PRIMARY KEY ("invd_id")
        );
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_invdetail_invoice'
            ) THEN
                ALTER TABLE "public"."InvoicesDetail"
                ADD CONSTRAINT fk_invdetail_invoice
                FOREIGN KEY (invd_invoice_id) REFERENCES "Invoices"(inv_id) ON DELETE CASCADE;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_invdetail_order_detail'
            ) THEN
                ALTER TABLE "public"."InvoicesDetail"
                ADD CONSTRAINT fk_invdetail_order_detail
                FOREIGN KEY (invd_order_detail_id) REFERENCES "OrdersDetails"(od_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_invdetail_study'
            ) THEN
                ALTER TABLE "public"."InvoicesDetail"
                ADD CONSTRAINT fk_invdetail_study
                FOREIGN KEY (invd_study_id) REFERENCES "StudiesLab"(id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_invdetail_created_by'
            ) THEN
                ALTER TABLE "public"."InvoicesDetail"
                ADD CONSTRAINT fk_invdetail_created_by
                FOREIGN KEY (invd_created_by) REFERENCES "AppUsers"(usr_id);
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS "public"."InvoicesDetail" CASCADE;')
    op.execute('DROP TABLE IF EXISTS "public"."Invoices" CASCADE;')

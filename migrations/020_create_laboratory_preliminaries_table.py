"""
Migration 020: Create LaboratoryPreliminaries table for storing preliminary
microbiology results (partial results per sequence from analyzers).

New table:
  - LaboratoryPreliminaries
    - lp_id                SERIAL PRIMARY KEY
    - lp_laboratory_id     INT NOT NULL → FK to Laboratories(l_id)
    - lp_secuence          INT NOT NULL
    - lp_result            TEXT
    - lp_date_preliminary  TIMESTAMP
    - analyzer             VARCHAR(255)

Safe to run even if the table already exists (uses IF NOT EXISTS).
"""

from alembic import op
import sqlalchemy as sa

revision = "020_create_laboratory_preliminaries_table"
down_revision = "019_add_document_control_to_dynamic_reports"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS "public"."LaboratoryPreliminaries" (
            "lp_id"              SERIAL       NOT NULL,
            "lp_laboratory_id"   INT          NOT NULL,
            "lp_secuence"        INT          NOT NULL,
            "lp_result"          TEXT,
            "lp_date_preliminary" TIMESTAMP,
            "analyzer"           VARCHAR(255),
            PRIMARY KEY ("lp_id")
        );
    """)

    # Add FK to Laboratories if it doesn't already exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_lab_preliminary_laboratory'
            ) THEN
                ALTER TABLE "public"."LaboratoryPreliminaries"
                ADD CONSTRAINT fk_lab_preliminary_laboratory
                FOREIGN KEY (lp_laboratory_id) REFERENCES "Laboratories"(l_id) ON DELETE CASCADE;
            END IF;
        END
        $$;
    """)

    # Index for faster lookups by laboratory
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_LaboratoryPreliminaries_lab_id"
        ON "public"."LaboratoryPreliminaries" (lp_laboratory_id);
    """)

    # Index for ordering by sequence
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_LaboratoryPreliminaries_lab_seq"
        ON "public"."LaboratoryPreliminaries" (lp_laboratory_id, lp_secuence);
    """)


def downgrade():
    op.execute('DROP TABLE IF EXISTS "public"."LaboratoryPreliminaries" CASCADE;')
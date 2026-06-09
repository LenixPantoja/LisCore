"""
Migration 021: Create AnnexedResult table for storing annexed PDFs to lab results.

New table:
  - AnnexedResult
    - ar_id                SERIAL PRIMARY KEY
    - ar_order_id          INT NOT NULL → FK to Orders(o_id)
    - ar_file              VARCHAR(500) NOT NULL — MinIO object name
    - ar_user_record_file  INT → FK to AppUsers(usr_id)
    - ar_created_at        TIMESTAMP
    - ar_updated_at        TIMESTAMP

Safe to run even if the table already exists (uses IF NOT EXISTS).
"""

from alembic import op
import sqlalchemy as sa

revision = "021_create_annexed_result_table"
down_revision = "020_create_laboratory_preliminaries_table"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS "public"."AnnexedResult" (
            "ar_id"               SERIAL       NOT NULL,
            "ar_order_id"         INT          NOT NULL,
            "ar_file"             VARCHAR(500) NOT NULL,
            "ar_user_record_file" INT,
            "ar_created_at"       TIMESTAMP,
            "ar_updated_at"       TIMESTAMP,
            PRIMARY KEY ("ar_id")
        );
    """)

    # Add FKs if they don't already exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_annexed_result_order'
            ) THEN
                ALTER TABLE "public"."AnnexedResult"
                ADD CONSTRAINT fk_annexed_result_order
                FOREIGN KEY (ar_order_id) REFERENCES "Orders"(o_id) ON DELETE CASCADE;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_annexed_result_user'
            ) THEN
                ALTER TABLE "public"."AnnexedResult"
                ADD CONSTRAINT fk_annexed_result_user
                FOREIGN KEY (ar_user_record_file) REFERENCES "AppUsers"(usr_id);
            END IF;
        END
        $$;
    """)

    # Index for faster lookups by order
    op.execute("""
        CREATE INDEX IF NOT EXISTS "ix_AnnexedResult_order_id"
        ON "public"."AnnexedResult" (ar_order_id);
    """)


def downgrade():
    op.execute('DROP TABLE IF EXISTS "public"."AnnexedResult" CASCADE;')
"""
Runner for migration 019: Add document-control columns to DynamicReports.

Usage:
    python utils/run_migration_019.py
"""
import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.core.config import settings

SQL_STATEMENTS = [
    'ALTER TABLE "DynamicReports" ADD COLUMN IF NOT EXISTS dr_code VARCHAR(50)',
    'ALTER TABLE "DynamicReports" ADD COLUMN IF NOT EXISTS dr_version VARCHAR(20)',
    'ALTER TABLE "DynamicReports" ADD COLUMN IF NOT EXISTS dr_emission_date VARCHAR(20)',
]


async def run() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        for sql in SQL_STATEMENTS:
            await conn.execute(text(sql))
            print(f"✓ {sql}")
    await engine.dispose()
    print("\nMigración 019 aplicada correctamente.")


if __name__ == "__main__":
    asyncio.run(run())

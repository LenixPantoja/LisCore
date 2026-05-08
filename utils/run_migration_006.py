import asyncio, sys
sys.path.insert(0, '.')
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

SQL = (
    'CREATE TABLE IF NOT EXISTS "RangesReferences" ('
    '    id SERIAL PRIMARY KEY,'
    '    range_type VARCHAR(50),'
    '    test_id INTEGER REFERENCES "TestsLab"(id),'
    '    gender VARCHAR(10),'
    '    age_type VARCHAR(10),'
    '    min_age INTEGER,'
    '    max_age INTEGER,'
    '    priority INTEGER,'
    '    created_at TIMESTAMP,'
    '    updated_at TIMESTAMP'
    ');'
)

SQL2 = 'CREATE INDEX IF NOT EXISTS ix_RangesReferences_test_id ON "RangesReferences"(test_id);'

SQL3 = (
    'CREATE TABLE IF NOT EXISTS "ReferencesValues" ('
    '    id SERIAL PRIMARY KEY,'
    '    ranges_references_id INTEGER REFERENCES "RangesReferences"(id),'
    '    min_value NUMERIC,'
    '    max_values NUMERIC,'
    '    text_value TEXT,'
    '    created_at TIMESTAMP,'
    '    updated_at TIMESTAMP'
    ');'
)

SQL4 = 'CREATE INDEX IF NOT EXISTS ix_ReferencesValues_ranges_references_id ON "ReferencesValues"(ranges_references_id);'


async def run():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text(SQL))
        await conn.execute(text(SQL2))
        await conn.execute(text(SQL3))
        await conn.execute(text(SQL4))
    print('OK - tablas creadas')
    await engine.dispose()

asyncio.run(run())

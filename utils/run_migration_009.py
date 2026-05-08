"""
Migration runner: adds num_decimal_result column to TestsLab table.
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()


async def run():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )
    await conn.execute(
        'ALTER TABLE "TestsLab" ADD COLUMN IF NOT EXISTS num_decimal_result INTEGER;'
    )
    print("OK: columna num_decimal_result agregada (o ya existia).")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(run())

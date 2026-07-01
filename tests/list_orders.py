import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sf() as db:
        # Try a few orders
        for oid in [1, 2, 3, 4, 5, 10, 20, 30, 50, 100]:
            result = await db.execute(
                text("SELECT o_id, o_number, o_order_state FROM \"Orders\" WHERE o_id = :oid"),
                {"oid": oid}
            )
            row = result.fetchone()
            if row:
                print(f"✅ Order ID {oid}: #{row[1]}, state={row[2]}")
            else:
                print(f"❌ Order ID {oid}: NOT FOUND")

        print("\n--- Last 10 orders ---")
        result = await db.execute(
            text("SELECT o_id, o_number, o_order_state, o_date FROM \"Orders\" ORDER BY o_id DESC LIMIT 10")
        )
        for row in result.fetchall():
            print(f"  ID={row[0]}, #{row[1]}, state={row[2]}, date={row[3]}")

    await engine.dispose()

asyncio.run(main())
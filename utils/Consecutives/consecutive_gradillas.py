"""
Gradilla consecutive number generator.

Format: DDMMAA-CONSECUTIVO
Example: 300626-1  (30/06/26 - consecutive 1)
"""

from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.seroteca.domain.models import Gradilla


async def generate_gradilla_number(db: AsyncSession) -> str:
    """
    Genera un consecutivo de gradilla con formato DDMMAA-CONSECUTIVO.
    El consecutivo se reinicia cada día. 
    Ejemplo: 300626-1, 300626-2, 010726-1
    """
    today = date.today()
    dd_mm_yy = today.strftime("%d%m%y")

    # Count how many gradillas were created today (by g_created_at date)
    stmt = select(func.count(Gradilla.g_id)).where(
        func.date(Gradilla.g_created_at) == today
    )
    result = await db.execute(stmt)
    count_today = result.scalar() or 0

    new_seq = count_today + 1

    return f"{dd_mm_yy}-{new_seq}"
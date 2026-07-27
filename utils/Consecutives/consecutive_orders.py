from datetime import date
from sqlalchemy import select
from app.domains.orders.domain.models import Order
from sqlalchemy.ext.asyncio import AsyncSession

async def generate_order_number(db: AsyncSession, order_date: date) -> str:
    """
    Genera un número de orden con formato DDMMYYCCCC
    Ejemplo: 0504260001 (Día 05, Mes 04, Año 26, Consecutivo 0001)
    """
    dd_mm_yy = order_date.strftime("%d%m%y")

    # Buscamos la última orden creada hoy para obtener el último consecutivo
    stmt = select(Order.o_number).where(Order.o_date == order_date).order_by(Order.o_id.desc()).limit(1)
    result = await db.execute(stmt)
    last_number = result.scalar()

    if last_number and len(last_number) == 10:
        try:
            # Extraemos el consecutivo CCCC (posiciones 6 a 10)
            current_seq = int(last_number[6:10])
            new_seq = str(current_seq + 1).zfill(4)
        except ValueError:
            new_seq = "0001"
    else:
        new_seq = "0001"

    return f"{dd_mm_yy}{new_seq}"
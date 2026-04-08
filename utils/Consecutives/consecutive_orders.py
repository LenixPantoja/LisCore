from datetime import date
from sqlalchemy import select
from app.domains.orders.domain.models import Order
from sqlalchemy.ext.asyncio import AsyncSession

async def generate_order_number(db: AsyncSession, order_date: date) -> str:
    """
    Genera un número de orden con formato MMDDCCCCYY
    Ejemplo: 0405000126 (Mes 04, Día 05, Consecutivo 0001, Año 26)
    """
    mm_dd = order_date.strftime("%m%d")
    yy = order_date.strftime("%y")

    # Buscamos la última orden creada hoy para obtener el último consecutivo
    stmt = select(Order.o_number).where(Order.o_date == order_date).order_by(Order.o_id.desc()).limit(1)
    result = await db.execute(stmt)
    last_number = result.scalar()

    if last_number and len(last_number) == 10:
        try:
            # Extraemos la parte central CCCC (posiciones 4 a 8)
            current_seq = int(last_number[4:8])
            new_seq = str(current_seq + 1).zfill(4)
        except ValueError:
            new_seq = "0001"
    else:
        new_seq = "0001"

    return f"{mm_dd}{new_seq}{yy}"
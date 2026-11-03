from datetime import date
from sqlalchemy import select, func
from app.domains.orders.domain.models import Order
from sqlalchemy.ext.asyncio import AsyncSession

from utils.Consecutives.consecutive_lock import lock_consecutive


async def generate_order_number(db: AsyncSession, order_date: date) -> str:
    """
    Genera un número de orden con formato DDMMYYCCCC
    Ejemplo: 0504260001 (Día 05, Mes 04, Año 26, Consecutivo 0001)

    Bloquea el consecutivo del día hasta el commit: si dos usuarios crean una
    orden al mismo tiempo, el segundo espera y recibe el número siguiente.
    """
    dd_mm_yy = order_date.strftime("%d%m%y")
    await lock_consecutive(db, f"order_number:{dd_mm_yy}")

    # Mayor número del día (mismo prefijo y 10 dígitos, así el orden de texto es el numérico)
    stmt = select(func.max(Order.o_number)).where(
        Order.o_number.like(f"{dd_mm_yy}%"),
        func.length(Order.o_number) == 10,
    )
    last_number = (await db.execute(stmt)).scalar()

    try:
        new_seq = int(last_number[6:10]) + 1 if last_number else 1
    except ValueError:
        new_seq = 1

    return f"{dd_mm_yy}{str(new_seq).zfill(4)}"

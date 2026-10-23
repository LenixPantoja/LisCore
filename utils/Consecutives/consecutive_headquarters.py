"""
Consecutivo de órdenes por sede.

Cada sede (Headquarters) lleva su propio contador en
Headquarters.order_consecutive_next, que va de 1 a 999999999.
"""

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.Headquarters.domain.models import Headquarter

HQ_CONSECUTIVE_MAX = 999_999_999


async def generate_headquarter_consecutive(db: AsyncSession, headquarter_id: int) -> int:
    """
    Reserva y retorna el siguiente consecutivo de la sede.

    El UPDATE ... RETURNING es atómico: Postgres bloquea la fila de la sede
    hasta que termine la transacción, así que si varios usuarios de la misma
    sede crean órdenes al mismo tiempo, cada uno recibe un número distinto
    (los demás esperan a que el primero confirme o revierta). Si la creación
    de la orden falla y se hace rollback, el contador también se revierte y no
    quedan huecos.
    """
    stmt = (
        update(Headquarter)
        .where(
            Headquarter.id == headquarter_id,
            Headquarter.order_consecutive_next <= HQ_CONSECUTIVE_MAX,
        )
        .values(order_consecutive_next=Headquarter.order_consecutive_next + 1)
        .returning(Headquarter.order_consecutive_next)
    )
    result = await db.execute(stmt)
    new_next = result.scalar()

    if new_next is None:
        exists = await db.execute(select(Headquarter.id).where(Headquarter.id == headquarter_id))
        if exists.scalar() is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La sede especificada no existe.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La sede {headquarter_id} alcanzó el consecutivo máximo ({HQ_CONSECUTIVE_MAX}).",
        )

    return new_next - 1


async def get_next_headquarter_consecutive(db: AsyncSession, headquarter_id: int) -> int | None:
    """Consulta (sin reservar) el próximo consecutivo de la sede. Solo informativo."""
    result = await db.execute(
        select(Headquarter.order_consecutive_next).where(Headquarter.id == headquarter_id)
    )
    return result.scalar()

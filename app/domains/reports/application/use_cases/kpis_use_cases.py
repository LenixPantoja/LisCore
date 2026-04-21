from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.domains.orders.domain.models import Order
from app.domains.orders.domain.constants import ORDER_STATE_PENDIENTE

ORDER_PRIORITY_URGENTE = 1


def _format_count(value: int) -> str:
    if value >= 1_000_000:
        n = value / 1_000_000
        return f"{int(n) if n == int(n) else round(n, 1)}M"
    if value >= 1_000:
        n = value / 1_000
        return f"{int(n) if n == int(n) else round(n, 1)}K"
    return str(value)


async def get_kpis(db: AsyncSession) -> dict:
    total_stmt = select(func.count(Order.o_id))
    total_orders = (await db.execute(total_stmt)).scalar_one()

    pending_stmt = select(func.count(Order.o_id)).where(
        Order.o_order_state == ORDER_STATE_PENDIENTE
    )
    total_pending_orders = (await db.execute(pending_stmt)).scalar_one()

    urgency_stmt = select(func.count(Order.o_id)).where(
        Order.o_priority == ORDER_PRIORITY_URGENTE
    )
    total_urgency_orders = (await db.execute(urgency_stmt)).scalar_one()

    return {
        "total_orders": _format_count(total_orders),
        "total_pending_orders": _format_count(total_pending_orders),
        "total_urgency_orders": _format_count(total_urgency_orders),
    }

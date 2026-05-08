from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from datetime import date
from typing import Optional

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.orders.domain.constants import ORDER_STATE_PENDIENTE, ORDER_STATES
from app.domains.masters.domain.models import WorkGroup
from app.domains.studieslab.domain.models import StudiesLab
from app.domains.Headquarters.domain.models import Headquarter

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


async def get_orders_by_work_group_by_date(db: AsyncSession, target_date: date) -> dict:
    stmt = (
        select(
            WorkGroup.wg_name.label("work_group"),
            func.count(Order.o_id.distinct()).label("total_orders"),
        )
        .outerjoin(StudiesLab, StudiesLab.work_groups_id == WorkGroup.wg_id)
        .outerjoin(OrdersDetail, OrdersDetail.od_study_id == StudiesLab.id)
        .outerjoin(
            Order,
            (Order.o_id == OrdersDetail.od_order_id) & (Order.o_date == target_date),
        )
        .group_by(WorkGroup.wg_id, WorkGroup.wg_name)
        .order_by(func.count(Order.o_id.distinct()).desc(), WorkGroup.wg_name)
    )
    rows = (await db.execute(stmt)).all()

    return {
        "date": target_date,
        "orders_by_work_group": [
            {"work_group": row.work_group, "total_orders": row.total_orders}
            for row in rows
        ],
    }


async def get_orders_by_sede_by_date(db: AsyncSession, target_date: date) -> dict:
    stmt = (
        select(
            Headquarter.id.label("hq_id"),
            Headquarter.name.label("sede"),
            func.count(Order.o_id.distinct()).label("total_orders"),
        )
        .outerjoin(
            Order,
            (Order.o_headquarter_id == Headquarter.id) & (Order.o_date == target_date),
        )
        .group_by(Headquarter.id, Headquarter.name)
        .order_by(func.count(Order.o_id.distinct()).desc(), Headquarter.name)
    )
    rows = (await db.execute(stmt)).all()

    orders_by_sede = [
        {"hq_id": row.hq_id, "sede": row.sede, "total_orders": row.total_orders}
        for row in rows
    ]
    total = sum(r["total_orders"] for r in orders_by_sede)

    return {
        "date": target_date,
        "total_orders": total,
        "orders_by_sede": orders_by_sede,
    }


async def get_orders_by_period(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    stmt = (
        select(
            extract("year", Order.o_date).label("year"),
            extract("month", Order.o_date).label("month"),
            Order.o_order_state.label("state_id"),
            func.count(Order.o_id).label("total"),
        )
        .where(Order.o_date.isnot(None))
        .group_by(
            extract("year", Order.o_date),
            extract("month", Order.o_date),
            Order.o_order_state,
        )
        .order_by(
            extract("year", Order.o_date).desc(),
            extract("month", Order.o_date).desc(),
            Order.o_order_state,
        )
    )

    if date_from:
        stmt = stmt.where(Order.o_date >= date_from)
    if date_to:
        stmt = stmt.where(Order.o_date <= date_to)

    rows = (await db.execute(stmt)).all()

    periods: dict[tuple, dict] = {}
    for row in rows:
        key = (int(row.year), int(row.month))
        if key not in periods:
            periods[key] = {"year": key[0], "month": key[1], "total_orders": 0, "states": []}
        state_entry = {
            "state_id": row.state_id,
            "state_name": ORDER_STATES.get(row.state_id, str(row.state_id)),
            "total": row.total,
        }
        periods[key]["states"].append(state_entry)
        periods[key]["total_orders"] += row.total

    return {"data": list(periods.values())}

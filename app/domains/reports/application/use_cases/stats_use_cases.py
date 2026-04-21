from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, cast, String, Integer, text
from datetime import date

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.orders.domain.constants import ORDER_STATES
from app.domains.masters.domain.models import WorkGroup
from app.domains.Headquarters.domain.models import Headquarter
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail
from app.domains.laboratories.domain.models import Laboratory


async def get_dashboard_stats(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    headquarter_id: Optional[int] = None,
) -> dict:
    # --- Filtro base de fechas ---
    def apply_date_filter(q, date_col):
        if date_from:
            q = q.filter(date_col >= date_from)
        if date_to:
            q = q.filter(date_col <= date_to)
        return q

    def apply_hq_filter(q):
        if headquarter_id:
            q = q.filter(Order.o_headquarter_id == headquarter_id)
        return q

    # 1. Cantidad de órdenes por estado
    state_counts_stmt = apply_hq_filter(
        apply_date_filter(
            select(Order.o_order_state, func.count(Order.o_id).label("total"))
            .group_by(Order.o_order_state),
            Order.o_date,
        )
    )
    state_rows = (await db.execute(state_counts_stmt)).all()
    orders_by_state = [
        {"state_id": row.o_order_state, "state_name": ORDER_STATES.get(row.o_order_state, str(row.o_order_state)), "total": row.total}
        for row in state_rows
    ]
    total_ingresadas = next((r["total"] for r in orders_by_state if r["state_id"] == 1), 0)
    total_pendientes = next((r["total"] for r in orders_by_state if r["state_id"] == 2), 0)

    # 2. Órdenes por work group
    wg_stmt = (
        apply_hq_filter(
            apply_date_filter(
                select(
                    WorkGroup.wg_name.label("work_group"),
                    func.count(Order.o_id.distinct()).label("total_orders"),
                )
                .join(OrdersDetail, OrdersDetail.od_order_id == Order.o_id)
                .join(StudiesLab, StudiesLab.id == OrdersDetail.od_study_id)
                .join(WorkGroup, WorkGroup.wg_id == StudiesLab.work_groups_id)
                .group_by(WorkGroup.wg_name),
                Order.o_date,
            )
        )
    )
    wg_rows = (await db.execute(wg_stmt)).all()
    orders_by_work_group = [{"work_group": r.work_group, "total_orders": r.total_orders} for r in wg_rows]

    # 3. Órdenes por sede
    hq_orders_stmt = apply_date_filter(
        select(
            Headquarter.name.label("sede"),
            Headquarter.id.label("hq_id"),
            func.count(Order.o_id).label("total_orders"),
        )
        .join(Order, Order.o_headquarter_id == Headquarter.id)
        .group_by(Headquarter.id, Headquarter.name),
        Order.o_date,
    )
    if headquarter_id:
        hq_orders_stmt = hq_orders_stmt.filter(Headquarter.id == headquarter_id)
    hq_orders_rows = (await db.execute(hq_orders_stmt)).all()
    orders_by_sede = [{"hq_id": r.hq_id, "sede": r.sede, "total_orders": r.total_orders} for r in hq_orders_rows]

    # 4. Estudios por sede
    hq_studies_stmt = apply_date_filter(
        select(
            Headquarter.name.label("sede"),
            Headquarter.id.label("hq_id"),
            func.count(OrdersDetail.od_id).label("total_studies"),
        )
        .join(Order, Order.o_headquarter_id == Headquarter.id)
        .join(OrdersDetail, OrdersDetail.od_order_id == Order.o_id)
        .group_by(Headquarter.id, Headquarter.name),
        Order.o_date,
    )
    if headquarter_id:
        hq_studies_stmt = hq_studies_stmt.filter(Headquarter.id == headquarter_id)
    hq_studies_rows = (await db.execute(hq_studies_stmt)).all()
    studies_by_sede = [{"hq_id": r.hq_id, "sede": r.sede, "total_studies": r.total_studies} for r in hq_studies_rows]

    # 5. Pruebas por sede
    hq_labs_stmt = apply_date_filter(
        select(
            Headquarter.name.label("sede"),
            Headquarter.id.label("hq_id"),
            func.count(Laboratory.l_id).label("total_labs"),
        )
        .join(Order, Order.o_headquarter_id == Headquarter.id)
        .join(OrdersDetail, OrdersDetail.od_order_id == Order.o_id)
        .join(Laboratory, Laboratory.l_order_detail_id == OrdersDetail.od_id)
        .group_by(Headquarter.id, Headquarter.name),
        Order.o_date,
    )
    if headquarter_id:
        hq_labs_stmt = hq_labs_stmt.filter(Headquarter.id == headquarter_id)
    hq_labs_rows = (await db.execute(hq_labs_stmt)).all()
    labs_by_sede = [{"hq_id": r.hq_id, "sede": r.sede, "total_labs": r.total_labs} for r in hq_labs_rows]

    # 6. Órdenes por día / mes / año
    def _time_group_query(period: str):
        if period == "day":
            label = func.date(Order.o_date).label("period")
        elif period == "month":
            label = func.to_char(Order.o_date, "YYYY-MM").label("period")
        else:  # year
            label = cast(extract("year", Order.o_date), Integer).label("period")
        stmt = apply_hq_filter(
            apply_date_filter(
                select(label, func.count(Order.o_id).label("total")).group_by(label).order_by(label),
                Order.o_date,
            )
        )
        return stmt

    day_rows = (await db.execute(_time_group_query("day"))).all()
    month_rows = (await db.execute(_time_group_query("month"))).all()
    year_rows = (await db.execute(_time_group_query("year"))).all()

    return {
        "total_orders_ingresadas": total_ingresadas,
        "total_orders_pendientes": total_pendientes,
        "orders_by_state": orders_by_state,
        "orders_by_work_group": orders_by_work_group,
        "orders_by_sede": orders_by_sede,
        "studies_by_sede": studies_by_sede,
        "labs_by_sede": labs_by_sede,
        "orders_by_day": [{"period": str(r.period), "total": r.total} for r in day_rows],
        "orders_by_month": [{"period": str(r.period), "total": r.total} for r in month_rows],
        "orders_by_year": [{"period": str(r.period), "total": r.total} for r in year_rows],
    }

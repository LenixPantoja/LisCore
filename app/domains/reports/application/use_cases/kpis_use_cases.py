from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, exists
from datetime import date
from typing import Optional

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.orders.domain.constants import ORDER_STATE_PENDIENTE, ORDER_STATES
from app.domains.masters.domain.models import WorkGroup
from app.domains.studieslab.domain.models import StudiesLab
from app.domains.Headquarters.domain.models import Headquarter
from app.domains.laboratories.domain.models import Laboratory
from app.domains.laboratories.domain.constants import LABORATORY_STATE_VALIDADA, LABORATORY_STATE_IMPRESO

ORDER_PRIORITY_URGENTE = 1
_VALIDATED_LAB_STATES = (LABORATORY_STATE_VALIDADA, LABORATORY_STATE_IMPRESO)


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


async def get_orders_by_work_group_by_date(db: AsyncSession, target_date: date, date_to: Optional[date] = None) -> dict:
    """Órdenes por área en un día (target_date) o, si llega date_to, en el rango target_date..date_to."""
    end_date = date_to if date_to and date_to >= target_date else target_date
    stmt = (
        select(
            WorkGroup.wg_name.label("work_group"),
            func.count(Order.o_id.distinct()).label("total_orders"),
        )
        .outerjoin(StudiesLab, StudiesLab.work_groups_id == WorkGroup.wg_id)
        .outerjoin(OrdersDetail, OrdersDetail.od_study_id == StudiesLab.id)
        .outerjoin(
            Order,
            (Order.o_id == OrdersDetail.od_order_id) & (Order.o_date >= target_date) & (Order.o_date <= end_date),
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


async def get_orders_by_sede_by_date(db: AsyncSession, target_date: date, date_to: Optional[date] = None) -> dict:
    """Órdenes por sede en un día (target_date) o, si llega date_to, en el rango target_date..date_to."""
    end_date = date_to if date_to and date_to >= target_date else target_date
    stmt = (
        select(
            Headquarter.id.label("hq_id"),
            Headquarter.name.label("sede"),
            func.count(Order.o_id.distinct()).label("total_orders"),
        )
        .outerjoin(
            Order,
            (Order.o_headquarter_id == Headquarter.id) & (Order.o_date >= target_date) & (Order.o_date <= end_date),
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
    """
    Solo cuenta órdenes cuyos laboratorios ya están validados (Validada /
    Laboratorio Impreso): la orden debe tener al menos una prueba, y ninguna
    de sus pruebas puede estar en un estado distinto de esos dos.
    """
    labs_of_order = (
        select(Laboratory.l_id)
        .select_from(Laboratory)
        .join(OrdersDetail, OrdersDetail.od_id == Laboratory.l_order_detail_id)
        .where(OrdersDetail.od_order_id == Order.o_id)
    )
    has_labs = exists(labs_of_order)
    has_unvalidated_lab = exists(
        labs_of_order.where(Laboratory.l_state.notin_(_VALIDATED_LAB_STATES))
    )

    stmt = (
        select(
            extract("year", Order.o_date).label("year"),
            extract("month", Order.o_date).label("month"),
            Order.o_order_state.label("state_id"),
            func.count(Order.o_id).label("total"),
        )
        .where(Order.o_date.isnot(None), has_labs, ~has_unvalidated_lab)
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


async def get_validation_by_work_group(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """
    Muestras (tubos: orden + tipo de muestra) de las órdenes ingresadas en el rango,
    por área (grupo de trabajo), separadas en:
      - validated: todas las pruebas del área en ese tubo validadas o impresas
        (las descartadas cuentan como resueltas).
      - pending:   alguna prueba del área en ese tubo todavía sin validar.
    Sin fechas se usa el día de hoy. Excluye órdenes anuladas.
    """
    from datetime import timedelta
    from sqlalchemy import text
    from utils.timezone import get_bogota_now

    today = get_bogota_now().date()
    start = date_from or today
    end = date_to or start
    if end < start:
        start, end = end, start

    rows = (await db.execute(text("""
        -- Una muestra = un tubo de la orden (orden + sufijo del tipo de muestra, igual
        -- que el código de barras). Se cuenta en cada área cuyos estudios van en ese tubo.
        WITH lab AS (
            SELECT o.o_id,
                   COALESCE(st.st_sufix, st.st_id) AS sfx,
                   s.work_groups_id                AS wg_id,
                   l.l_state
            FROM "Orders" o
            JOIN "OrdersDetails" od ON od.od_order_id = o.o_id AND od.od_cancelled = 0
            JOIN "StudiesLab" s     ON s.id = od.od_study_id
            JOIN "Laboratories" l   ON l.l_order_detail_id = od.od_id
            JOIN "TestsLab" t       ON t.id = l.l_test_id
            JOIN "SampleTypes" st   ON st.st_id = t.samples_type_id
            WHERE o.o_created_at >= :start AND o.o_created_at < :end_excl
              AND o.o_order_state <> 7
        ),
        smp AS (
            SELECT o_id, sfx, wg_id,
                   bool_and(l_state IN (3, 4, 5)) AS all_done,
                   bool_or(l_state IN (3, 4))     AS any_validated
            FROM lab
            GROUP BY o_id, sfx, wg_id
        )
        SELECT smp.wg_id, COALESCE(wg.wg_name, 'Sin área') AS wg_name,
               COUNT(*) FILTER (WHERE all_done AND any_validated) AS validated,
               COUNT(*) FILTER (WHERE NOT all_done)               AS pending
        FROM smp
        LEFT JOIN "Work_groups" wg ON wg.wg_id = smp.wg_id
        GROUP BY smp.wg_id, wg.wg_name
    """), {"start": start, "end_excl": end + timedelta(days=1)})).all()

    def slices(field: str) -> list[dict]:
        items = [
            {"wg_id": r.wg_id, "wg_name": r.wg_name, "total": int(getattr(r, field))}
            for r in rows if getattr(r, field)
        ]
        return sorted(items, key=lambda x: (-x["total"], x["wg_name"]))

    validated, pending = slices("validated"), slices("pending")
    return {
        "date_from": start,
        "date_to": end,
        "validated": validated,
        "pending": pending,
        "total_validated": sum(i["total"] for i in validated),
        "total_pending": sum(i["total"] for i in pending),
    }

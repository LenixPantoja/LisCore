from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, cast, String, Integer, text
from datetime import date

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.orders.domain.constants import ORDER_STATES
from app.domains.masters.domain.models import WorkGroup, Service, SexType
from app.domains.Headquarters.domain.models import Headquarter
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail
from app.domains.laboratories.domain.models import Laboratory
from app.domains.patients.domain.models import Patient


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


def _apply_order_date_filter(stmt, date_from: Optional[date], date_to: Optional[date]):
    if date_from:
        stmt = stmt.filter(Order.o_date >= date_from)
    if date_to:
        stmt = stmt.filter(Order.o_date <= date_to)
    return stmt


async def get_production_by_work_group(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """Cantidad (y %) de estudios (OrdersDetail) procesados por grupo de trabajo."""
    stmt = (
        select(
            WorkGroup.wg_id.label("work_group_id"),
            WorkGroup.wg_name.label("work_group"),
            func.count(OrdersDetail.od_id).label("total"),
        )
        .select_from(OrdersDetail)
        .join(Order, Order.o_id == OrdersDetail.od_order_id)
        .join(StudiesLab, StudiesLab.id == OrdersDetail.od_study_id)
        .join(WorkGroup, WorkGroup.wg_id == StudiesLab.work_groups_id)
        .group_by(WorkGroup.wg_id, WorkGroup.wg_name)
        .order_by(func.count(OrdersDetail.od_id).desc())
    )
    stmt = _apply_order_date_filter(stmt, date_from, date_to)
    rows = (await db.execute(stmt)).all()

    total = sum(r.total for r in rows)
    items = [
        {
            "work_group_id": r.work_group_id,
            "work_group": r.work_group,
            "total": r.total,
            "percentage": round((r.total / total * 100), 2) if total else 0.0,
        }
        for r in rows
    ]
    return {"total": total, "items": items}


async def get_top_studies(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 10,
) -> dict:
    """Top N estudios (StudiesLab) más solicitados."""
    stmt = (
        select(
            StudiesLab.id.label("study_id"),
            StudiesLab.name.label("study_name"),
            func.count(OrdersDetail.od_id).label("total"),
        )
        .select_from(OrdersDetail)
        .join(Order, Order.o_id == OrdersDetail.od_order_id)
        .join(StudiesLab, StudiesLab.id == OrdersDetail.od_study_id)
        .group_by(StudiesLab.id, StudiesLab.name)
        .order_by(func.count(OrdersDetail.od_id).desc())
        .limit(limit)
    )
    stmt = _apply_order_date_filter(stmt, date_from, date_to)
    rows = (await db.execute(stmt)).all()

    items = [
        {"study_id": r.study_id, "study_name": r.study_name, "total": r.total}
        for r in rows
    ]
    return {"items": items}


async def get_studies_by_service(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """Cantidad (y %) de estudios (OrdersDetail) agrupados por servicio de la orden."""
    stmt = (
        select(
            Service.id.label("service_id"),
            Service.name.label("service_name"),
            func.count(OrdersDetail.od_id).label("total"),
        )
        .select_from(OrdersDetail)
        .join(Order, Order.o_id == OrdersDetail.od_order_id)
        .outerjoin(Service, Service.id == Order.o_service_id)
        .group_by(Service.id, Service.name)
        .order_by(func.count(OrdersDetail.od_id).desc())
    )
    stmt = _apply_order_date_filter(stmt, date_from, date_to)
    rows = (await db.execute(stmt)).all()

    total = sum(r.total for r in rows)
    items = [
        {
            "service_id": r.service_id,
            "service_name": r.service_name,
            "total": r.total,
            "percentage": round((r.total / total * 100), 2) if total else 0.0,
        }
        for r in rows
    ]
    return {"total": total, "items": items}


async def get_kpis_summary(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """KPIs del dashboard: pacientes atendidos (por género), órdenes, pruebas, promedio y paciente con más atenciones."""
    # Total de órdenes procesadas
    orders_stmt = _apply_order_date_filter(select(func.count(Order.o_id.distinct())), date_from, date_to)
    total_orders = (await db.execute(orders_stmt)).scalar_one()

    # Total de pruebas recibidas (Laboratories)
    tests_stmt = _apply_order_date_filter(
        select(func.count(Laboratory.l_id))
        .select_from(Laboratory)
        .join(OrdersDetail, OrdersDetail.od_id == Laboratory.l_order_detail_id)
        .join(Order, Order.o_id == OrdersDetail.od_order_id),
        date_from,
        date_to,
    )
    total_tests = (await db.execute(tests_stmt)).scalar_one()

    avg_tests_per_order = round(total_tests / total_orders, 2) if total_orders else 0.0

    # Pacientes atendidos (únicos) y desglose por género
    patients_stmt = _apply_order_date_filter(
        select(
            SexType.code.label("sex_code"),
            func.count(Patient.pt_id.distinct()).label("total"),
        )
        .select_from(Order)
        .join(Patient, Patient.pt_id == Order.o_his_id)
        .outerjoin(SexType, SexType.id == Patient.pt_sex_type)
        .group_by(SexType.code),
        date_from,
        date_to,
    )
    sex_rows = (await db.execute(patients_stmt)).all()
    # Códigos de Sex_Types: 'H' = Hombre (masculino), 'M' = Mujer (femenino)
    male_patients = sum(r.total for r in sex_rows if r.sex_code == "H")
    female_patients = sum(r.total for r in sex_rows if r.sex_code == "M")
    total_patients = sum(r.total for r in sex_rows)

    # Paciente con más atenciones (órdenes)
    top_patient_stmt = _apply_order_date_filter(
        select(
            Patient.pt_id,
            Patient.pt_Number_document.label("document"),
            func.concat(
                Patient.pt_firts_name, " ", Patient.pt_last_name
            ).label("name"),
            func.count(Order.o_id.distinct()).label("total_visits"),
        )
        .select_from(Order)
        .join(Patient, Patient.pt_id == Order.o_his_id)
        .group_by(Patient.pt_id, Patient.pt_Number_document, Patient.pt_firts_name, Patient.pt_last_name)
        .order_by(func.count(Order.o_id.distinct()).desc())
        .limit(1),
        date_from,
        date_to,
    )
    top_row = (await db.execute(top_patient_stmt)).first()
    top_patient = (
        {
            "pt_id": top_row.pt_id,
            "document": top_row.document,
            "name": top_row.name,
            "total_visits": top_row.total_visits,
        }
        if top_row
        else None
    )

    return {
        "total_patients": total_patients,
        "male_patients": male_patients,
        "female_patients": female_patients,
        "total_orders": total_orders,
        "total_tests": total_tests,
        "avg_tests_per_order": avg_tests_per_order,
        "top_patient": top_patient,
    }

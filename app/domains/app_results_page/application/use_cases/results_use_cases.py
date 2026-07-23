from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.app_results_page.domain.helpers import bucket_age_label, full_name, resolve_sex
from app.domains.enterprises.domain.models import Enterprise
from app.domains.laboratories.domain.constants import (
    LABORATORY_STATE_IMPRESO,
    LABORATORY_STATE_VALIDADA,
    LABORATORY_STATES,
)
from app.domains.laboratories.domain.models import Laboratory
from app.domains.orders.domain.constants import ORDER_STATES
from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.patients.domain.models import Patient
from app.domains.studieslab.domain.models import StudiesTestDetail
from app.domains.testslabs.domain.models import RangeReference

# Estados de Laboratory que se consideran "resultado definitivo" para el paciente.
_VALIDATED_LAB_STATES = {LABORATORY_STATE_VALIDADA, LABORATORY_STATE_IMPRESO}
_PENDING_STATE_LABEL = "Pendiente"


def _parse_search_date(value: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _matched_state_ids(search: str) -> list[int]:
    needle = search.lower()
    return [state_id for state_id, name in ORDER_STATES.items() if needle in name.lower()]


def _format_result(lab: Laboratory) -> Optional[str]:
    if lab.l_result:
        return lab.l_result
    if lab.l_result_num is not None:
        return str(lab.l_result_num)
    return None


def _format_datetime(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    return value.strftime("%d-%m-%Y %I:%M %p")


async def _fetch_required_map(
    db: AsyncSession, study_test_pairs: set[tuple[int, int]]
) -> dict[tuple[int, int], bool]:
    """Devuelve, para cada (study_id, test_id), si la prueba es obligatoria en ese estudio."""
    if not study_test_pairs:
        return {}

    study_ids = {pair[0] for pair in study_test_pairs}
    test_ids = {pair[1] for pair in study_test_pairs}
    result = await db.execute(
        select(StudiesTestDetail).where(
            StudiesTestDetail.studies_id.in_(study_ids),
            StudiesTestDetail.tests_id.in_(test_ids),
        )
    )
    return {(std.studies_id, std.tests_id): bool(std.is_required) for std in result.scalars().all()}


async def _fetch_ranges_by_test(db: AsyncSession, test_ids: set[int]) -> dict[int, list[dict]]:
    """Devuelve, por test_id, la lista de rangos de referencia configurados con sus valores."""
    if not test_ids:
        return {}

    result = await db.execute(
        select(RangeReference)
        .where(RangeReference.test_id.in_(test_ids))
        .options(selectinload(RangeReference.reference_values))
        .order_by(RangeReference.test_id, RangeReference.priority.asc().nullslast())
    )
    ranges_by_test: dict[int, list[dict]] = {}
    for rr in result.scalars().all():
        ranges_by_test.setdefault(rr.test_id, []).append({
            "range_type": rr.range_type,
            "gender": rr.gender,
            "age_type": rr.age_type,
            "min_age": rr.min_age,
            "max_age": rr.max_age,
            "priority": rr.priority,
            "values": [
                {
                    "min_value": float(rv.min_value) if rv.min_value is not None else None,
                    "max_values": float(rv.max_values) if rv.max_values is not None else None,
                    "text_value": rv.text_value,
                }
                for rv in rr.reference_values
            ],
        })
    return ranges_by_test


async def _fetch_studies_by_order(
    db: AsyncSession,
    order_ids: list[int],
    only_show_validated: bool = False,
) -> dict[int, list[dict]]:
    """Para cada o_id, agrupa los resultados de laboratorio por estudio.

    Si `only_show_validated` es True, un resultado solo se muestra cuando su
    l_state está validado (Validada / Laboratorio Impreso); en cualquier otro
    caso se oculta el valor y se reporta como "Pendiente", sin importar si la
    prueba es obligatoria (is_required) o no dentro del estudio.
    """
    if not order_ids:
        return {}

    stmt = (
        select(Laboratory)
        .join(OrdersDetail, OrdersDetail.od_id == Laboratory.l_order_detail_id)
        .where(OrdersDetail.od_order_id.in_(order_ids))
        .options(
            selectinload(Laboratory.test),
            selectinload(Laboratory.order_detail).selectinload(OrdersDetail.study),
        )
        .order_by(OrdersDetail.od_order_id, OrdersDetail.od_study_id, Laboratory.l_id)
    )
    result = await db.execute(stmt)
    labs = result.scalars().all()

    required_map = await _fetch_required_map(db, {
        (lab.order_detail.od_study_id, lab.l_test_id)
        for lab in labs
        if lab.order_detail and lab.l_test_id
    })
    ranges_by_test = await _fetch_ranges_by_test(db, {lab.l_test_id for lab in labs if lab.l_test_id})

    studies_by_order: dict[int, dict[int, dict]] = {}
    study_order_seq: dict[int, list[int]] = {}

    for lab in labs:
        detail = lab.order_detail
        if not detail:
            continue
        order_id = detail.od_order_id
        study = detail.study
        study_id = study.id if study else 0

        order_studies = studies_by_order.setdefault(order_id, {})
        if study_id not in order_studies:
            order_studies[study_id] = {
                "study_name": study.name if study else "—",
                "results": [],
            }
            study_order_seq.setdefault(order_id, []).append(study_id)

        is_validated = lab.l_state in _VALIDATED_LAB_STATES
        if only_show_validated and not is_validated:
            result_value = None
            state_label = _PENDING_STATE_LABEL
            validation_date = None
        else:
            result_value = _format_result(lab)
            state_label = LABORATORY_STATES.get(lab.l_state, str(lab.l_state))
            validation_date = _format_datetime(lab.l_date_validatie)

        order_studies[study_id]["results"].append({
            "test_name": lab.test.name if lab.test else "—",
            "result": result_value,
            "units": lab.test.units if lab.test else None,
            "l_state": state_label,
            "l_date_validatie": validation_date,
            "is_required": required_map.get((study_id, lab.l_test_id), False),
            "reference_ranges": ranges_by_test.get(lab.l_test_id, []),
            "alternative_range_value": lab.test.alternative_range_value if lab.test else None,
        })

    return {
        order_id: [order_studies[study_id] for study_id in study_order_seq.get(order_id, [])]
        for order_id, order_studies in studies_by_order.items()
    }


async def list_patient_orders(
    db: AsyncSession,
    patient: Patient,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> dict:
    query = select(Order).where(Order.o_his_id == patient.pt_id)

    if search:
        conditions = [Order.o_number.ilike(f"%{search}%")]
        parsed_date = _parse_search_date(search)
        if parsed_date:
            conditions.append(Order.o_date == parsed_date)
        matched_states = _matched_state_ids(search)
        if matched_states:
            conditions.append(Order.o_order_state.in_(matched_states))
        query = query.where(or_(*conditions))

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    skip = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Order.o_date.desc(), Order.o_id.desc()).offset(skip).limit(page_size)
    )
    orders = result.scalars().all()

    studies_by_order = await _fetch_studies_by_order(db, [o.o_id for o in orders], only_show_validated=True)
    patient_document = patient.pt_Number_document
    patient_fullname = full_name(patient)

    items = [
        {
            "o_id": order.o_id,
            "o_number": order.o_number,
            "o_autorizacion": order.o_autorizacion or "",
            "document_number": patient_document,
            "fullname_patient": patient_fullname,
            "o_date": order.o_date,
            "o_order_state": ORDER_STATES.get(order.o_order_state, str(order.o_order_state)),
            "studies": studies_by_order.get(order.o_id, []),
        }
        for order in orders
    ]

    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def list_enterprise_orders(
    db: AsyncSession,
    enterprise: Enterprise,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> dict:
    query = (
        select(Order)
        .join(Patient, Patient.pt_id == Order.o_his_id)
        .where(Order.o_enterprise_id == enterprise.en_id)
        .options(selectinload(Order.patient))
    )

    if search:
        conditions = [
            Order.o_number.ilike(f"%{search}%"),
            Order.o_autorizacion.ilike(f"%{search}%"),
            Patient.pt_Number_document.ilike(f"%{search}%"),
        ]
        parsed_date = _parse_search_date(search)
        if parsed_date:
            conditions.append(Order.o_date == parsed_date)
        matched_states = _matched_state_ids(search)
        if matched_states:
            conditions.append(Order.o_order_state.in_(matched_states))
        query = query.where(or_(*conditions))

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    skip = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Order.o_date.desc(), Order.o_id.desc()).offset(skip).limit(page_size)
    )
    orders = result.scalars().all()

    studies_by_order = await _fetch_studies_by_order(db, [o.o_id for o in orders], only_show_validated=True)

    items = [
        {
            "o_id": order.o_id,
            "o_number": order.o_number,
            "io_number_request": order.o_autorizacion or "",
            "document_number": order.patient.pt_Number_document if order.patient else None,
            "fullname_patient": full_name(order.patient),
            "o_date": order.o_date,
            "age": bucket_age_label(order.patient.pt_date_of_birth) if order.patient else None,
            "sex": resolve_sex(order.patient) if order.patient else None,
            "o_order_state": ORDER_STATES.get(order.o_order_state, str(order.o_order_state)),
            "studies": studies_by_order.get(order.o_id, []),
        }
        for order in orders
    ]

    return {"total": total, "page": page, "page_size": page_size, "items": items}

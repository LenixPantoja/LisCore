from decimal import Decimal
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.contractstariffs.domain.models import TariffDetail
from app.domains.masters.domain.models import Diagnosis
from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.patients.domain.models import Patient
from app.domains.studieslab.domain.models import StudiesLab
from app.domains.users.infrastructure.models import AppUser
from app.domains.reports.infrastructure.pos.pos_generator import (
    build_pos_ticket,
    pos_pdf_to_base64,
)


async def generate_pos_ticket(db: AsyncSession, order_id: int) -> dict:
    """
    Generate an 80mm POS ticket PDF for the given order ID.

    Returns a dict with filename, base64_pdf, order_number and order_id.
    """
    # 1. Load order with all needed relations
    result = await db.execute(
        select(Order)
        .filter(Order.o_id == order_id)
        .options(
            selectinload(Order.patient).selectinload(Patient.document_type),
            selectinload(Order.patient).selectinload(Patient.sex_type),
            selectinload(Order.enterprise),
            selectinload(Order.diagnosis),
        )
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden con ID {order_id} no encontrada.",
        )

    # 2. Load the user who entered the order (no FK, query separately)
    app_user: AppUser | None = None
    if order.o_AppUser_id:
        app_user = await db.get(AppUser, order.o_AppUser_id)

    # 3. Get distinct study IDs from OrdersDetail for this order
    study_ids_result = await db.execute(
        select(distinct(OrdersDetail.od_study_id)).where(
            OrdersDetail.od_order_id == order_id
        )
    )
    study_ids: List[int] = study_ids_result.scalars().all()

    # 4. Load StudiesLab records for those study IDs
    studies_result = await db.execute(
        select(StudiesLab).filter(StudiesLab.id.in_(study_ids))
    )
    study_map: dict = {s.id: s.name for s in studies_result.scalars().all()}

    # 5. Load tariff values per study (if the order has a tariff assigned)
    tariff_values: dict = {}
    if order.o_tariff_id and study_ids:
        tv_result = await db.execute(
            select(TariffDetail).filter(
                TariffDetail.td_tariff_id == order.o_tariff_id,
                TariffDetail.td_studie_id.in_(study_ids),
            )
        )
        for td in tv_result.scalars().all():
            tariff_values[td.td_studie_id] = td.td_value

    # 6. Build ordered (study_name, tariff_value) list
    studies: List[Tuple] = [
        (study_map.get(sid, f"Estudio {sid}"), tariff_values.get(sid))
        for sid in study_ids
    ]

    # 7. Generate PDF
    pdf_bytes = build_pos_ticket(
        order=order,
        patient=order.patient,
        enterprise=order.enterprise,
        diagnosis=order.diagnosis,
        app_user=app_user,
        studies=studies,
    )
    b64 = pos_pdf_to_base64(pdf_bytes)

    patient_doc = (
        order.patient.pt_Number_document if order.patient else "paciente"
    )
    filename = f"ticket_pos_{order.o_number}_{patient_doc}.pdf"

    return {
        "filename": filename,
        "base64_pdf": b64,
        "order_number": order.o_number,
        "order_id": order_id,
    }

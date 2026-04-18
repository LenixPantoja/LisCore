from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.laboratories.domain.models import Laboratory
from app.domains.reports.infrastructure.pdf_generator import build_laboratory_pdf, pdf_to_base64


async def generate_laboratory_report(db: AsyncSession, order_id: int) -> dict:
    # 1. Cargar la orden con paciente y empresa
    result = await db.execute(
        select(Order)
        .filter(Order.o_id == order_id)
        .options(
            selectinload(Order.patient),
            selectinload(Order.enterprise),
        )
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden con ID {order_id} no encontrada.",
        )

    patient = order.patient

    # 2. Cargar laboratorios de la orden con test y estudio
    labs_result = await db.execute(
        select(Laboratory)
        .join(OrdersDetail, OrdersDetail.od_id == Laboratory.l_order_detail_id)
        .filter(OrdersDetail.od_order_id == order_id)
        .options(
            selectinload(Laboratory.test),
            selectinload(Laboratory.order_detail).selectinload(OrdersDetail.study),
        )
        .order_by(Laboratory.l_id)
    )
    laboratories = labs_result.scalars().all()

    # 3. Generar PDF
    pdf_bytes = build_laboratory_pdf(order, patient, laboratories)
    b64 = pdf_to_base64(pdf_bytes)

    # 4. Nombre de archivo sugerido
    patient_doc = patient.pt_Number_document if patient else "paciente"
    filename = f"resultado_{order.o_number}_{patient_doc}.pdf"

    patient_name = _full_name(patient)

    return {
        "filename": filename,
        "base64_pdf": b64,
        "order_number": order.o_number,
        "patient_name": patient_name,
    }


def _full_name(patient) -> str:
    if not patient:
        return "—"
    parts = [
        patient.pt_firts_name,
        patient.pt_middle_name or "",
        patient.pt_last_name,
        patient.pt_second_last_name or "",
    ]
    return " ".join(p for p in parts if p).strip()

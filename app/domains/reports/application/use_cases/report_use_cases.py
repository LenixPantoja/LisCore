from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.laboratories.domain.models import Laboratory
from app.domains.studieslab.domain.models import StudiesLab
from app.domains.enterprises.domain.models import Enterprise
from app.domains.reports.infrastructure.pdf_generator import (
    build_laboratory_pdf, 
    pdf_to_base64,
    _full_name  # Importar la función desde pdf_generator
)


async def generate_laboratory_report(db: AsyncSession, order_id: int) -> dict:
    # 1. Cargar la orden con paciente y empresa
    result = await db.execute(
        select(Order)
        .filter(Order.o_id == order_id)
        .options(
            selectinload(Order.patient),
            selectinload(Order.enterprise).selectinload(Enterprise.regimen),
            selectinload(Order.enterprise).selectinload(Enterprise.classification),
            selectinload(Order.enterprise).selectinload(Enterprise.document_type),
            selectinload(Order.enterprise).selectinload(Enterprise.city),
            selectinload(Order.enterprise).selectinload(Enterprise.liability_type),
            selectinload(Order.service),
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
            selectinload(Laboratory.order_detail)
            .selectinload(OrdersDetail.study)
            .selectinload(StudiesLab.work_group),
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

    patient_name = _full_name(patient)  # Usar la función importada

    return {
        "filename": filename,
        "base64_pdf": b64,
        "order_number": order.o_number,
        "patient_name": patient_name,
    }
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.laboratories.domain.models import Laboratory
from app.domains.laboratories.domain.constants import LABORATORY_STATE_VALIDADA
from app.domains.studieslab.domain.models import StudiesLab
from app.domains.enterprises.domain.models import Enterprise
from app.domains.reports.infrastructure.pdf_generator import (
    build_laboratory_pdf,
    pdf_to_base64,
    _full_name,
)
from app.shared.utils.range_evaluator import evaluate_reference_range


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

    # 3. Bloquear si algún estudio contiene al menos una prueba confidencial
    has_confidential = any(
        lab.test and lab.test.is_confidential
        for lab in laboratories
    )
    if has_confidential:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La orden contiene pruebas confidenciales. No es posible generar el reporte en PDF.",
        )

    # 4. Filtrar solo estudios completamente validados
    labs_by_study: dict[int, list] = defaultdict(list)
    for lab in laboratories:
        study_key = lab.l_order_detail_id
        labs_by_study[study_key].append(lab)

    validated_labs = [
        lab
        for study_labs in labs_by_study.values()
        if all(lab.l_state >= LABORATORY_STATE_VALIDADA for lab in study_labs)
        for lab in study_labs
    ]

    # 5. Evaluar rangos de referencia y adjuntarlos a cada lab
    patient_dob = getattr(patient, "pt_date_of_birth", None)
    patient_sex = getattr(patient, "pt_sex_type", None)

    for lab in validated_labs:
        result_num = None
        result_text = None
        if lab.l_result_num is not None:
            result_num = float(lab.l_result_num)
        elif lab.l_result:
            try:
                result_num = float(str(lab.l_result).replace(",", "."))
            except (ValueError, AttributeError):
                result_text = lab.l_result

        range_type, ref_min, ref_max = (None, None, None)
        if lab.l_test_id and (result_num is not None or result_text):
            range_type, ref_min, ref_max = await evaluate_reference_range(
                db,
                lab.l_test_id,
                result_num,
                patient_dob,
                patient_sex,
                result_text=result_text,
            )
        lab.__dict__["_ref_type"] = range_type
        lab.__dict__["_ref_min"] = float(ref_min) if ref_min is not None else None
        lab.__dict__["_ref_max"] = float(ref_max) if ref_max is not None else None

    # 6. Generar PDF
    pdf_bytes = build_laboratory_pdf(order, patient, validated_labs)
    b64 = pdf_to_base64(pdf_bytes)

    # 7. Nombre de archivo sugerido
    patient_doc = patient.pt_Number_document if patient else "paciente"
    filename = f"resultado_{order.o_number}_{patient_doc}.pdf"

    patient_name = _full_name(patient)  # Usar la función importada

    return {
        "filename": filename,
        "base64_pdf": b64,
        "order_number": order.o_number,
        "patient_name": patient_name,
    }
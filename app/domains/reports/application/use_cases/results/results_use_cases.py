from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.laboratories.domain.models import Laboratory
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail
from app.domains.enterprises.domain.models import Enterprise
from app.domains.patients.domain.models import Patient
from app.domains.reports.infrastructure.pdf_generator import (
    build_laboratory_pdf,
    pdf_to_base64,
    merge_pdfs,
    _full_name,
)
from app.shared.utils.range_evaluator import evaluate_reference_range


async def generate_laboratory_report_raw(db: AsyncSession, order_id: int) -> dict:
    """
    Genera el PDF de resultados de laboratorio SIN filtrar por estado
    de los laboratorios ni de la orden. Muestra todos los resultados
    registrados tal cual están.
    """
    # 1. Cargar la orden con paciente y empresa
    result = await db.execute(
        select(Order)
        .filter(Order.o_id == order_id)
        .options(
            selectinload(Order.patient).selectinload(Patient.city),
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

    # 2. Cargar TODOS los laboratorios de la orden sin filtrar por estado
    labs_result = await db.execute(
        select(Laboratory)
        .join(OrdersDetail, OrdersDetail.od_id == Laboratory.l_order_detail_id)
        .join(StudiesLab, StudiesLab.id == OrdersDetail.od_study_id)
        .outerjoin(
            StudiesTestDetail,
            (StudiesTestDetail.studies_id == OrdersDetail.od_study_id)
            & (StudiesTestDetail.tests_id == Laboratory.l_test_id),
        )
        .filter(OrdersDetail.od_order_id == order_id)
        .options(
            selectinload(Laboratory.test),
            selectinload(Laboratory.user_validation),
            selectinload(Laboratory.order_detail)
            .selectinload(OrdersDetail.study)
            .selectinload(StudiesLab.work_group),
        )
        .order_by(
            StudiesLab.order_of_print.nulls_last(),
            StudiesTestDetail.order_print.nulls_last(),
            Laboratory.l_id,
        )
    )
    laboratories = labs_result.scalars().all()

    # 3. Evaluar rangos de referencia y adjuntarlos a cada lab
    patient_dob = getattr(patient, "pt_date_of_birth", None)
    patient_sex = getattr(patient, "pt_sex_type", None)

    for lab in laboratories:
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

    # 4. Construir mapa de firmas: {study_id: [{user_name, usr_Signature}]}
    signatures_map: dict[int, list[dict]] = {}
    _seen_sig: set[tuple[int, int]] = set()
    for lab in laboratories:
        if not lab.l_user_validation_id or not lab.user_validation:
            continue
        user = lab.user_validation
        _study_id = None
        if lab.order_detail and lab.order_detail.study:
            _study_id = lab.order_detail.study.id
        if _study_id is None:
            continue
        _user_key = (_study_id, user.usr_id)
        if _user_key not in _seen_sig:
            _seen_sig.add(_user_key)
            _user_name = " ".join(filter(None, [
                user.usr_first_name,
                user.usr_middle_name or None,
                user.usr_last_name,
                user.usr_second_last_name or None,
            ])).upper()
            signatures_map.setdefault(_study_id, []).append({
                "user_name": _user_name,
                "usr_Signature": user.usr_Signature,
                "usr_document_number": user.usr_document_number or "",
            })

    # 5. Cargar PDFs anexos
    from app.domains.annexes.domain.models import AnnexedResult
    from utils.minio_client import download_annexed_pdf

    annex_result = await db.execute(
        select(AnnexedResult)
        .where(AnnexedResult.ar_order_id == order_id)
        .order_by(AnnexedResult.ar_created_at.asc())
    )
    annexed_records = annex_result.scalars().all()

    annex_pdfs: list[bytes] = []
    for ann in annexed_records:
        pdf_data = download_annexed_pdf(ann.ar_file)
        if pdf_data:
            annex_pdfs.append(pdf_data)

    # 6. Generar PDF
    pdf_bytes = build_laboratory_pdf(order, patient, laboratories, signatures_map)

    # 7. Anexar PDFs al final si existen
    if annex_pdfs:
        pdf_bytes = merge_pdfs(pdf_bytes, annex_pdfs)
    b64 = pdf_to_base64(pdf_bytes)

    # 8. Nombre de archivo sugerido
    patient_doc = patient.pt_Number_document if patient else "paciente"
    filename = f"resultado_{order.o_number}_{patient_doc}.pdf"

    patient_name = _full_name(patient)

    return {
        "filename": filename,
        "base64_pdf": b64,
        "order_number": order.o_number,
        "patient_name": patient_name,
    }
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.laboratories.domain.models import Laboratory
from app.domains.laboratories.domain.constants import LABORATORY_STATE_VALIDADA, LABORATORY_STATE_IMPRESO
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


async def generate_laboratory_report(
    db: AsyncSession,
    order_id: int,
    include_results: bool = True,
    study_ids: Optional[list[int]] = None,
) -> dict:
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

    validated_labs: list = []
    signatures_map: dict[int, list[dict]] = {}

    if include_results:
        # 2. Cargar laboratorios de la orden con test y estudio
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

        # 3. Filtrar solo estudios completamente validados, agrupando por estudio
        #    real (od_study_id) y respetando pruebas requeridas/no requeridas:
        #    misma lógica que get_full_order_details_by_id en
        #    app/domains/orders/application/use_cases/order_use_cases.py.
        labs_by_study: dict[int, list] = defaultdict(list)
        for lab in laboratories:
            study_id = lab.order_detail.od_study_id if lab.order_detail else None
            if study_id is not None:
                labs_by_study[study_id].append(lab)

        if study_ids:
            requested = set(study_ids)
            missing = requested - labs_by_study.keys()
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Los estudios {sorted(missing)} no pertenecen a la orden {order_id}.",
                )
            labs_by_study = {sid: labs for sid, labs in labs_by_study.items() if sid in requested}

        required_tests_by_study: dict[int, set[int]] = {}
        if labs_by_study:
            std_result = await db.execute(
                select(StudiesTestDetail).where(
                    StudiesTestDetail.studies_id.in_(labs_by_study.keys()),
                    StudiesTestDetail.is_required == True,
                )
            )
            for std in std_result.scalars().all():
                required_tests_by_study.setdefault(std.studies_id, set()).add(std.tests_id)

        states_with_results = {LABORATORY_STATE_VALIDADA, LABORATORY_STATE_IMPRESO}

        validated_labs = []
        for study_id, study_labs in labs_by_study.items():
            required_test_ids = required_tests_by_study.get(study_id, set())
            labs_by_test = {
                lab.l_test_id: lab.l_state for lab in study_labs if lab.l_test_id is not None
            }

            if required_test_ids:
                # Solo las pruebas requeridas determinan si el estudio está listo
                study_ready = all(
                    labs_by_test.get(tid, 0) in states_with_results for tid in required_test_ids
                )
            else:
                # Sin pruebas requeridas definidas: todas deben estar validadas
                study_ready = bool(study_labs) and all(
                    lab.l_state in states_with_results for lab in study_labs
                )

            if study_ready:
                validated_labs.extend(study_labs)

        # 4. Evaluar rangos de referencia y adjuntarlos a cada lab
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

        # 5. Construir mapa de firmas: {study_id: [{user_name, usr_Signature}]}
        _seen_sig: set[tuple[int, int]] = set()
        for lab in validated_labs:
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

    # 6. Cargar PDFs anexos
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

    # 7. Generar PDF principal
    pdf_bytes = build_laboratory_pdf(order, patient, validated_labs, signatures_map)

    # 8. Anexar PDFs al final si existen
    if annex_pdfs:
        pdf_bytes = merge_pdfs(pdf_bytes, annex_pdfs)
    b64 = pdf_to_base64(pdf_bytes)

    # 9. Nombre de archivo sugerido
    patient_doc = patient.pt_Number_document if patient else "paciente"
    filename = f"resultado_{order.o_number}_{patient_doc}.pdf"

    patient_name = _full_name(patient)  # Usar la función importada

    return {
        "filename": filename,
        "base64_pdf": b64,
        "order_number": order.o_number,
        "patient_name": patient_name,
    }


async def generate_validated_laboratory_report(
    db: AsyncSession, order_id: int, study_ids: Optional[list[int]] = None
) -> dict:
    """
    Punto de entrada de /api/reports/laboratory-results: genera siempre el PDF,
    incluyendo únicamente los estudios cuyos laboratorios estén completamente
    validados (considerando pruebas requeridas y no requeridas, ver paso 3 de
    generate_laboratory_report). Los estudios que aún no cumplen esa condición
    no aparecen en el PDF, sin importar el estado general de la orden.

    Si se envía `study_ids`, se evalúa esa misma condición pero restringida a
    esos estudios: solo aparecen en el PDF los que, dentro del subconjunto
    solicitado, ya están completamente validados.
    """
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden con ID {order_id} no encontrada.",
        )

    return await generate_laboratory_report(db, order_id, include_results=True, study_ids=study_ids)
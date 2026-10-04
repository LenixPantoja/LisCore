from collections import defaultdict
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.laboratories.domain.models import Laboratory
from app.domains.laboratories.domain.constants import LABORATORY_STATE_VALIDADA, LABORATORY_STATE_IMPRESO
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail
from app.domains.testslabs.domain.models import TestsLab
from app.domains.enterprises.domain.models import Enterprise
from app.domains.patients.domain.models import Patient
from app.domains.reports.infrastructure.pdf_generator import (
    build_laboratory_pdf,
    pdf_to_base64,
    merge_pdfs,
    _full_name,
    _group_by_study,
    _resolve_sex,
    _signature_group_last_flags,
)
from app.shared.utils.range_evaluator import evaluate_reference_range

# Nombres de objeto fijos del bucket 'resources' de MinIO (logos y marca de
# agua institucionales, los mismos para todas las órdenes).
RESOURCE_OBJECT_NAMES = {
    "LOGO1": "Logo1.png",
    "LOGO2": "Logo2.png",
    "MARCA_DE_AGUA": "marca_de_agua.png",
}


async def _load_order_and_validated_labs(
    db: AsyncSession,
    order_id: int,
    include_results: bool = True,
    study_ids: Optional[list[int]] = None,
) -> tuple[Order, Any, list, dict[int, list[dict]]]:
    """
    Carga la orden + paciente y, si include_results, los laboratorios de
    estudios completamente validados (considerando pruebas requeridas/no
    requeridas — ver comentario del paso 3 más abajo), con sus rangos de
    referencia evaluados y el mapa de firmas por estudio ya construido.

    Es la lógica compartida entre el PDF de resultados
    (generate_laboratory_report) y el endpoint de datos estructurados para
    plantillas (generate_laboratory_report_data): ambos deben mostrar
    exactamente los mismos estudios/pruebas validados y las mismas firmas.

    Retorna (order, patient, validated_labs, signatures_map).
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
                selectinload(Laboratory.test).selectinload(TestsLab.technique),
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

    return order, patient, validated_labs, signatures_map


async def _load_annex_pdfs(db: AsyncSession, order_id: int) -> list[bytes]:
    """
    Carga los PDFs anexos (AnnexedResult) de una orden, en el orden en que
    se subieron, listos para fusionar al final del PDF principal de
    resultados. Compartido entre el flujo local (reportlab) y la v2 que
    delega el renderizado a un servicio externo.
    """
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
    return annex_pdfs


async def generate_laboratory_report(
    db: AsyncSession,
    order_id: int,
    include_results: bool = True,
    study_ids: Optional[list[int]] = None,
) -> dict:
    order, patient, validated_labs, signatures_map = await _load_order_and_validated_labs(
        db, order_id, include_results=include_results, study_ids=study_ids
    )

    # 6. Cargar PDFs anexos
    annex_pdfs = await _load_annex_pdfs(db, order_id)

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


async def generate_laboratory_report_data(
    db: AsyncSession, order_id: int, study_ids: Optional[list[int]] = None
) -> dict:
    """
    Punto de entrada de /api/reports/laboratory-results/report-data: retorna
    los mismos resultados validados que /api/reports/laboratory-results (ver
    generate_validated_laboratory_report) pero como datos estructurados
    ("parametros" + "estudios") en vez de un PDF, pensados para alimentar un
    motor de plantillas externo.

    Reutiliza exactamente la misma carga/filtrado de estudios validados y el
    mismo mapa de firmas que el PDF (_load_order_and_validated_labs), y el
    mismo agrupador por estudio (_group_by_study) que arma cada fila de
    resultado — incluyendo el resultado compuesto (l_result_comp) y el
    nombre de objeto de la gráfica (l_result_graphic) tal cual los usa el
    PDF — así que ambos endpoints muestran siempre los mismos estudios,
    pruebas y validadores. La única diferencia es que aquí las firmas y las
    gráficas se resuelven a URLs presignadas de MinIO en vez de descargarse
    como imagen para incrustar en el documento.
    """
    from utils.minio_client import get_signature_url, get_graphic_url, get_resource_url

    order, patient, validated_labs, signatures_map = await _load_order_and_validated_labs(
        db, order_id, include_results=True, study_ids=study_ids
    )

    is_female, sex_label = _resolve_sex(patient)

    parametros = {
        "NOMBRE_PACIENTE": _full_name(patient),
        "DOCUMENTO_PACIENTE": patient.pt_Number_document if patient else "—",
        "EMPRESA": order.enterprise.en_name if order.enterprise else "—",
        "MUNICIPIO": (patient.city.city_name if patient and patient.city else None) or "—",
        "SERVICIO": order.service.name if order.service else "—",
        "NUMERO_ORDEN": order.o_number or "—",
        "EDAD": order.o_age or "—",
        "GENERO": sex_label,
        "FECHA_INGRESO_ORDEN": order.o_date.strftime("%d/%m/%Y") if order.o_date else "—",
        # Logos y marca de agua fijos del sistema, tomados del bucket
        # 'resources' de MinIO (ver RESOURCE_OBJECT_NAMES más abajo).
        "LOGO1": get_resource_url(RESOURCE_OBJECT_NAMES["LOGO1"]),
        "LOGO2": get_resource_url(RESOURCE_OBJECT_NAMES["LOGO2"]),
        "MARCA_DE_AGUA": get_resource_url(RESOURCE_OBJECT_NAMES["MARCA_DE_AGUA"]),
    }

    # Método por estudio: técnica de la primera prueba del estudio que tenga
    # una (TestsLab.technique). No existe un campo de método a nivel de
    # estudio, así que se deriva de sus pruebas, igual que el resto de datos
    # de "estudios" se deriva de los laboratorios agrupados.
    method_by_study: dict[int, str] = {}
    for lab in validated_labs:
        study_id = lab.order_detail.od_study_id if lab.order_detail else None
        if study_id is None or study_id in method_by_study:
            continue
        if lab.test and lab.test.technique and lab.test.technique.name:
            method_by_study[study_id] = lab.test.technique.name

    grupos_trabajo: list[dict] = []
    for wg_group in _group_by_study(validated_labs, is_female):
        # Igual que en el PDF (build_laboratory_pdf): si varios estudios
        # consecutivos del mismo grupo de trabajo fueron validados por
        # exactamente el mismo bacteriólogo (o el mismo conjunto de
        # bacteriólogos), la firma no se repite en cada uno — solo el
        # último estudio de esa racha trae VALIDADORES con la firma.
        last_of_group = _signature_group_last_flags(wg_group["studies"], signatures_map)

        estudios: list[dict] = []
        for idx, study in enumerate(wg_group["studies"]):
            validadores = []
            if last_of_group[idx]:
                for sig_info in signatures_map.get(study["id"], []):
                    validador = {"USUARIO_VALIDADOR": sig_info["user_name"]}
                    sig_url = get_signature_url(sig_info["usr_Signature"])
                    if sig_url:
                        validador["FIRMA_BACTERIOLOGO"] = sig_url
                    validadores.append(validador)

            pruebas = []
            for row in study["rows"]:
                units = row["units"] or ""
                resultado = row["result"] or ""
                referencia = row["reference"] or ""
                prueba = {
                    "NOMBRE_PRUEBA": row["test_name"],
                    "RESULTADO_PRUEBA": resultado,
                    "VALOR_REFERENCIA": f"{referencia} {units}".strip() if referencia else "",
                }
                alt_range = (row.get("alternative_range_value") or "").strip()
                if alt_range:
                    prueba["RANGO_ALTERNATIVO"] = alt_range
                if row.get("result_comp"):
                    prueba["RESULTADO_COMPUESTO_PRUEBA"] = row["result_comp"]
                if row.get("note"):
                    prueba["NOTAS_VALIDACION_PRUEBA"] = row["note"]
                graphic_url = get_graphic_url(row.get("graphic_object_name"))
                if graphic_url:
                    prueba["GRAFICA"] = graphic_url
                pruebas.append(prueba)

            estudios.append({
                "NOMBRE_ESTUDIO": study["name"],
                "METODO": method_by_study.get(study["id"], ""),
                "FECHA_VALIDACION_ESTUDIO": (
                    study["validation_date"].strftime("%d/%m/%Y %H:%M")
                    if study.get("validation_date") else None
                ),
                "VALIDADORES": validadores,
                "pruebas": pruebas,
            })

        grupos_trabajo.append({
            "GRUPO_TRABAJO": wg_group["wg_name"],
            "estudios": estudios,
        })

    return {"parametros": parametros, "grupos_trabajo": grupos_trabajo}


async def generate_laboratory_report_v2(
    db: AsyncSession,
    order_id: int,
    renderer_host: str,
    study_ids: Optional[list[int]] = None,
) -> dict:
    """
    Punto de entrada de /api/v2/reports/laboratory-results: funciona igual que
    /api/reports/laboratory-results (ver generate_validated_laboratory_report
    — mismos estudios validados, mismos PDFs anexos fusionados al final), pero
    en vez de armar el PDF localmente con reportlab arma los mismos datos
    estructurados que /laboratory-results/report-data (parametros +
    grupos_trabajo, ver generate_laboratory_report_data) y se los envía al
    servicio externo de renderizado de PDF, que corre en el mismo host que
    este backend (puerto PDF_RENDERER_PORT) y responde con el PDF ya armado
    en crudo.
    """
    from app.integrations.pdf_renderer.client import pdf_renderer_client

    report_data = await generate_laboratory_report_data(db, order_id, study_ids)
    annex_pdfs = await _load_annex_pdfs(db, order_id)

    try:
        pdf_bytes = await pdf_renderer_client.render(renderer_host, report_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al generar el PDF de resultados: {exc}",
        )

    if annex_pdfs:
        pdf_bytes = merge_pdfs(pdf_bytes, annex_pdfs)
    b64 = pdf_to_base64(pdf_bytes)

    parametros = report_data["parametros"]
    order_number = parametros.get("NUMERO_ORDEN") or "orden"
    patient_doc = parametros.get("DOCUMENTO_PACIENTE") or "paciente"

    return {
        "filename": f"resultado_{order_number}_{patient_doc}.pdf",
        "base64_pdf": b64,
        "order_number": order_number,
        "patient_name": parametros.get("NOMBRE_PACIENTE") or "—",
    }
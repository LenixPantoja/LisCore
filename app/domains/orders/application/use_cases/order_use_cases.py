from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.orders.infrastructure.repository import OrderRepository
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.shared.utils.range_evaluator import (
    evaluate_reference_range,
    bulk_fetch_ranges,
    evaluate_reference_range_sync,
)
from utils.minio_client import get_graphic_url
from app.domains.testslabs.infrastructure.testslab_format_complete_repository import (
    TestslabFormatCompleteRepository,
)

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.orders.domain.constants import ORDER_STATE_INGRESADA, ORDER_DETAIL_STATE_INGRESADO
from app.domains.laboratories.domain.constants import LABORATORY_STATE_SIN_RESULTADOS
from app.domains.samples.domain.models import SamplesOrder
from app.domains.samples.domain.constants import SAMPLE_ORDER_STATE_NO_INGRESADA
from app.domains.laboratories.domain.models import Laboratory
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail
from app.domains.testslabs.domain.models import TestsLab
from app.domains.billing.domain.models import Invoice, InvoiceDetail
from app.domains.billing.domain.constants import (
    INVOICE_STATE_CREADA,
    INVOICE_TYPE_FACTURA_VENTA,
    INVOICE_SUB_TYPE_FACTURA_CONTADO,
    INVOICE_SUB_TYPE_FACTURA_CREDITO,
    INVOICE_STATES,
    INVOICE_TYPES,
    INVOICE_SUB_TYPES,
)
from app.domains.Headquarters.domain.models import Headquarter
from app.domains.contractstariffs.domain.models import TariffDetail, ContractTariff, Contract
from utils.Consecutives.consecutive_orders import generate_order_number
from utils.Consecutives.consecutive_invoices import generate_invoice_number
from utils.timezone import get_bogota_now
from utils.trace import register_trace
from app.domains.traces.constants import OPERATION_CREATE_ORDER

async def create_order(db: AsyncSession, data: dict):
    studies_ids = data.pop("studies", [])
    if not studies_ids:
        raise HTTPException(status_code=400, detail="Debe solicitar al menos un estudio.")

    try:
        # 0. Validar que todos los estudios pertenezcan a la tarifa (si se indicó una)
        tariff_id_check = data.get("o_tariff_id")
        if tariff_id_check:
            tariff_study_ids = await OrderRepository.get_study_ids_for_tariff(db, tariff_id_check)
            studies_not_in_tariff = [sid for sid in studies_ids if sid not in tariff_study_ids]
            if studies_not_in_tariff:
                study_result = await db.execute(
                    select(StudiesLab).where(StudiesLab.id.in_(studies_not_in_tariff))
                )
                missing_studies = study_result.scalars().all()
                missing_info = [f"{s.name} ({s.code})" for s in missing_studies]
                found_ids = {s.id for s in missing_studies}
                for sid in studies_not_in_tariff:
                    if sid not in found_ids:
                        missing_info.append("Estudio desconocido")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Los siguientes estudios no están en la tarifa seleccionada: {'; '.join(missing_info)}",
                )

        # 1. Crear el encabezado de la Orden
        # La fecha se asigna automáticamente si no se envía
        if not data.get("o_date"):
            data["o_date"] = get_bogota_now().date()
        # Generamos el número de orden automáticamente ignorando el del request
        data["o_number"] = await generate_order_number(db, data.get("o_date"))
        # Estado inicial de la orden: Ingresada
        data["o_order_state"] = ORDER_STATE_INGRESADA
        data["o_cancelled"] = 0

        order = await OrderRepository.create(db, data)
        await db.flush() # Obtenemos o_id sin confirmar la transacción todavía        
        # Diccionario para evitar duplicar tipos de muestra en una misma orden
        # st_sufix → (first_st_id, set_of_st_ids) - agrupa por sufijo
        sample_suffix_map: dict[int, tuple[int, set[int]]] = {}
        # Mapa study_id → primer od_id creado (para InvoiceDetail)
        study_od_map: dict[int, int] = {}
        # Pruebas ya registradas en la orden (evita duplicados entre estudios)
        seen_test_ids: set[int] = set()

        for study_id in studies_ids:
            # 2. Consultar StudiesTestDetail para obtener las pruebas y tipos de muestra
            stmt = (
                select(StudiesTestDetail)
                .filter(StudiesTestDetail.studies_id == study_id)
                .options(selectinload(StudiesTestDetail.test))
            )
            result = await db.execute(stmt)
            test_links = result.scalars().all()

            if not test_links:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El estudio con ID {study_id} no tiene exámenes configurados en StudiesTestDetail."
                )

            # 3. Crear un OrdersDetail por estudio y un Laboratory por prueba única
            for link in test_links:
                order_detail = OrdersDetail(
                    od_order_id=order.o_id,
                    od_study_id=study_id,
                    od_state=ORDER_DETAIL_STATE_INGRESADO,
                    od_cancelled=0
                )
                db.add(order_detail)
                await db.flush()  # Para obtener od_id

                # Registrar el primer od_id de este estudio para la factura
                if study_id not in study_od_map:
                    study_od_map[study_id] = order_detail.od_id

                # Crear el registro de laboratorio solo si la prueba no existe ya en esta orden
                if link.tests_id not in seen_test_ids:
                    blank_result = Laboratory(
                        l_order_detail_id=order_detail.od_id,
                        l_test_id=link.tests_id,
                        l_state=LABORATORY_STATE_SIN_RESULTADOS
                    )
                    db.add(blank_result)
                    seen_test_ids.add(link.tests_id)

                # 4. Recolectar tipos de muestra para SamplesOrder agrupando por st_sufix
                #    Si dos SampleTypes tienen el mismo sufijo, solo se crea un SamplesOrder
                if link.test and link.test.samples_type_id:
                    from app.domains.samples.domain.models import SampleType
                    st_obj = await db.get(SampleType, link.test.samples_type_id)
                    st_sufix = (st_obj.st_sufix if st_obj and st_obj.st_sufix is not None else link.test.samples_type_id)
                    if st_sufix not in sample_suffix_map:
                        sample_suffix_map[st_sufix] = (link.test.samples_type_id, set())
                    sample_suffix_map[st_sufix][1].add(link.test.samples_type_id)

        # 6. Generar automáticamente registros de muestras (SamplesOrder)
        #    Se agrupa por sufix: si dos SampleTypes comparten el mismo sufijo,
        #    solo se crea un registro SamplesOrder (con el primer st_id como FK)
        for st_sufix, (first_st_id, _all_st_ids) in sample_suffix_map.items():
            sample_order = SamplesOrder(
                so_order_id=order.o_id,
                so_sample_type_id=first_st_id,
                so_barcode=f"{order.o_number}{st_sufix}",
                so_state=SAMPLE_ORDER_STATE_NO_INGRESADA,
                so_number_studies=len(studies_ids)
            )
            db.add(sample_order)

        # 7. Crear Factura automáticamente
        prefix = "INV"
        headquarter_id = data.get("o_headquarter_id")
        if headquarter_id:
            hq = await db.get(Headquarter, headquarter_id)
            if hq and hq.prefix:
                prefix = hq.prefix.strip()

        inv_number = await generate_invoice_number(db, prefix)

        unique_study_ids = list(dict.fromkeys(studies_ids))  # elimina duplicados preservando orden

        # Determinar el contrato activo para esta tarifa + empresa
        tariff_id = data.get("o_tariff_id")
        enterprise_id = data.get("o_enterprise_id")
        contract_tariff_id: int | None = None
        inv_sub_type: int | None = None

        if tariff_id:
            ct_stmt = (
                select(ContractTariff)
                .join(Contract, ContractTariff.ct_contract_id == Contract.co_id)
                .where(
                    ContractTariff.ct_tariff_id == tariff_id,
                    Contract.co_enterprise_id == enterprise_id,
                    Contract.co_active == True,
                )
                .limit(1)
            )
            ct_result = await db.execute(ct_stmt)
            ct = ct_result.scalars().first()

            if ct:
                contract_tariff_id = ct.ct_id
                contract = await db.get(Contract, ct.ct_contract_id)
                if contract and contract.co_billing_type is not None:
                    # co_billing_type=1 → crédito, co_billing_type=2 → contado
                    if contract.co_billing_type == 1:
                        inv_sub_type = INVOICE_SUB_TYPE_FACTURA_CREDITO
                    elif contract.co_billing_type == 2:
                        inv_sub_type = INVOICE_SUB_TYPE_FACTURA_CONTADO

        # Calcular subtotal desde tarifas
        invoice_subtotal = None
        inv_details_data: list[dict] = []

        for study_id in unique_study_ids:
            td_value = None
            if tariff_id:
                td_result = await db.execute(
                    select(TariffDetail).filter(
                        TariffDetail.td_tariff_id == tariff_id,
                        TariffDetail.td_studie_id == study_id,
                    )
                )
                td = td_result.scalars().first()
                if td:
                    td_value = td.td_value

            if td_value is not None:
                invoice_subtotal = (invoice_subtotal or 0) + td_value

            inv_details_data.append({
                "study_id": study_id,
                "od_id": study_od_map.get(study_id),
                "value": td_value,
            })

        invoice = Invoice(
            inv_number=inv_number,
            inv_date=data.get("o_date"),
            inv_enterprise_id=enterprise_id,
            inv_patient_id=data.get("o_his_id"),
            inv_contract_id=contract_tariff_id,
            inv_created_by=data.get("o_AppUser_id"),
            tariff_id=tariff_id,
            inv_subtotal=invoice_subtotal,
            inv_total=invoice_subtotal,
            inv_state=INVOICE_STATE_CREADA,
            inv_type=INVOICE_TYPE_FACTURA_VENTA,
            inv_sub_type_invoice=inv_sub_type,
        )
        db.add(invoice)
        await db.flush()

        for det in inv_details_data:
            inv_detail = InvoiceDetail(
                invd_invoice_id=invoice.inv_id,
                invd_order_detail_id=det["od_id"],
                invd_study_id=det["study_id"],
                invd_value=det["value"],
                invd_discount=None,
                invd_total=det["value"],
                invd_created_by=data.get("o_AppUser_id"),
            )
            db.add(inv_detail)

        # 8. Registrar trazas: un registro general + uno por cada estudio
        usr_id = data.get("o_AppUser_id")

        # Registro general de la orden
        await register_trace(
            db=db,
            operation_type=OPERATION_CREATE_ORDER,
            operation_description="Nueva orden",
            usr_id=usr_id,
            order_id=order.o_id,
        )

        # Cargar códigos de los estudios para la descripción
        studies_result = await db.execute(
            select(StudiesLab.id, StudiesLab.code).where(StudiesLab.id.in_(unique_study_ids))
        )
        study_code_map = {row.id: row.code for row in studies_result.all()}

        for study_id in unique_study_ids:
            study_code = study_code_map.get(study_id, str(study_id))
            await register_trace(
                db=db,
                operation_type=OPERATION_CREATE_ORDER,
                operation_description=f"Adición estudio {study_id} - {study_code}",
                usr_id=usr_id,
                order_id=order.o_id
            )

        await db.commit()
        await db.refresh(order)
        return order

    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig)
        if "o_his_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El paciente con ID {data.get('o_his_id')} no existe.")
        if "o_enterprise_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La empresa/convenio no existe.")
        if "o_tariff_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La tarifa seleccionada no existe.")
        if "o_diagnoses_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El diagnóstico especificado no es válido.")
        
        if "so_barcode" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conflicto de duplicidad en el código de barras de la muestra. El consecutivo falló.")

        # Manejo del error específico que probablemente te está pasando:
        if "Laboratories_l_order_detail_id_key" in error_msg or "l_order_detail_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail="Error: La tabla Laboratories tiene una restricción UNIQUE en l_order_detail_id que impide múltiples resultados por estudio.")

        if "o_scholarity" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nivel de escolaridad especificado no es válido.")
        if "o_headquarter_id" in error_msg or "Headquarters" in error_msg: # Assuming 'Headquarters' is the table name
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La sede especificada no existe.")
        if "o_AppUser_id" in error_msg or "Users" in error_msg: # Assuming 'Users' is the table name
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario de la aplicación especificado no existe.")
        
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error de integridad al crear la orden.")


async def cancel_order_studies(db: AsyncSession, o_id: int, study_ids: list[int]) -> dict:
    """Cancels specific studies from an order and cleans up related records."""
    result = await OrderRepository.cancel_studies(db, o_id, study_ids)
    if result["not_found"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada.")
    return result


async def list_orders(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    order_number: Optional[str] = None,
    patient_document: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    order_state: Optional[int] = None,
    search: Optional[str] = None
):
    items, total = await OrderRepository.get_paginated(
        db,
        skip,
        limit,
        order_number=order_number,
        patient_document=patient_document,
        start_date=start_date,
        end_date=end_date,
        order_state=order_state,
        search=search
    )

    # Calcular dinámicamente el o_order_state para cada orden según is_required
    # Solo para órdenes en estados transitorios (Ingresada=1, Pendiente=2, Con Resultados=3)
    DYNAMIC_STATES = {1, 2, 3}
    order_ids = [order.o_id for order in items if order.o_order_state in DYNAMIC_STATES]
    if order_ids:
        computed_states = await _compute_orders_state(db, order_ids)
        for order in items:
            if order.o_id in computed_states:
                order.o_order_state = computed_states[order.o_id]

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_order_by_id(db: AsyncSession, o_id: int):
    order = await OrderRepository.get_by_id(db, o_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")
    # Calcular dinámicamente el o_order_state según is_required
    # Solo si el estado actual es transitorio (Ingresada=1, Pendiente=2, Con Resultados=3)
    if order.o_order_state in {1, 2, 3}:
        computed_states = await _compute_orders_state(db, [order.o_id])
        if order.o_id in computed_states:
            order.o_order_state = computed_states[order.o_id]
    return order

async def update_order(db: AsyncSession, o_id: int, data: dict):
    try:
        order = await OrderRepository.update(db, o_id, data)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")
        return order
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error al actualizar la orden por conflicto de datos.")

async def get_next_order_number(db: AsyncSession):
    """Get the next order number (last + 1)"""
    next_number = await OrderRepository.get_next_order_number(db)
    return {"next_order_number": next_number}

async def get_order_details_paginated_by_number(
    db: AsyncSession, 
    o_number: str, 
    skip_labs: int = 0, 
    limit_labs: int = 100,
    skip_tests: int = 0, 
    limit_tests: int = 100
):
    # 1. Obtener orden principal
    order = await OrderRepository.get_order_by_number(db, o_number)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")

    # 2. Consultar laboratorios y pruebas paginados
    labs, total_labs = await OrderRepository.get_laboratories_paginated(db, order.o_id, skip_labs, limit_labs)
    tests, total_tests = await OrderRepository.get_tests_paginated(db, order.o_id, skip_tests, limit_tests)

    # 3. Enriquecer laboratorios con rangos de referencia
    #    Se hace un único batch query para todos los test_ids en vez de N queries individuales.
    patient = order.patient
    patient_dob = getattr(patient, "pt_date_of_birth", None) if patient else None
    patient_sex = getattr(patient, "pt_sex_type", None) if patient else None

    test_ids_with_result = list({
        lab.l_test_id for lab in labs
        if lab.l_test_id and (lab.l_result_num is not None or lab.l_result)
    })
    ranges_by_test = await bulk_fetch_ranges(db, test_ids_with_result)

    # Batch-fetch formats for all test_ids present in labs (with or without result)
    all_test_ids = list({lab.l_test_id for lab in labs if lab.l_test_id})
    formats_by_test = await TestslabFormatCompleteRepository.get_formats_by_testslab_ids(db, all_test_ids)

    enriched_labs = []
    for lab in labs:
        range_type, ref_min, ref_max = (None, None, None)
        result_num = None
        result_text = None

        if lab.l_result_num is not None:
            result_num = float(lab.l_result_num)
        elif lab.l_result:
            try:
                result_num = float(str(lab.l_result).replace(",", "."))
            except (ValueError, AttributeError):
                result_text = lab.l_result

        if lab.l_test_id and (result_num is not None or result_text):
            test_ranges = ranges_by_test.get(lab.l_test_id, [])
            range_type, ref_min, ref_max = evaluate_reference_range_sync(
                test_ranges, result_num, patient_dob, patient_sex, result_text=result_text
            )

        lab.__dict__["range_type"] = range_type
        lab.__dict__["value_range_reference_min"] = float(ref_min) if ref_min is not None else None
        lab.__dict__["value_range_reference_max"] = float(ref_max) if ref_max is not None else None

        if lab.l_result_graphic:
            lab.l_result_graphic = get_graphic_url(lab.l_result_graphic)

        lab.__dict__["formats_complete"] = [
            link.format_complete.fc_name
            for link in formats_by_test.get(lab.l_test_id, [])
            if link.format_complete
        ]

        enriched_labs.append(lab)

    # Enriquecer tests con formats_complete
    enriched_tests = []
    for test in tests:
        test.__dict__["formats_complete"] = [
            link.format_complete.fc_name
            for link in formats_by_test.get(test.id, [])
            if link.format_complete
        ]
        enriched_tests.append(test)

    return {
        "order": order,
        "patient": patient,
        "laboratories": {
            "total": total_labs,
            "skip": skip_labs,
            "limit": limit_labs,
            "items": enriched_labs
        },
        "tests": {
            "total": total_tests,
            "skip": skip_tests,
            "limit": limit_tests,
            "items": enriched_tests
        },
        "samples": await OrderRepository.get_samples_by_order_id(db, order.o_id),
    }

async def get_full_order_details_by_id(db: AsyncSession, o_id: int):
    # Sin paginación
    order = await OrderRepository.get_by_id(db, o_id) # Carga relaciones: patient, service, diagnosis, enterprise, schooling, tariff, details→study
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")
        
    labs, _ = await OrderRepository.get_laboratories_paginated(db, order.o_id, 0, 10000)
    tests, _ = await OrderRepository.get_tests_paginated(db, order.o_id, 0, 10000)
    samples = await OrderRepository.get_samples_by_order_id(db, order.o_id)

    # Enriquecer laboratorios con rangos de referencia, formatos y gráficos
    patient = order.patient
    patient_dob = getattr(patient, "pt_date_of_birth", None) if patient else None
    patient_sex = getattr(patient, "pt_sex_type", None) if patient else None

    test_ids_with_result = list({
        lab.l_test_id for lab in labs
        if lab.l_test_id and (lab.l_result_num is not None or lab.l_result)
    })
    ranges_by_test = await bulk_fetch_ranges(db, test_ids_with_result)

    all_test_ids = list({lab.l_test_id for lab in labs if lab.l_test_id})
    formats_by_test = await TestslabFormatCompleteRepository.get_formats_by_testslab_ids(db, all_test_ids)

    for lab in labs:
        range_type, ref_min, ref_max = (None, None, None)
        result_num = None
        result_text = None

        if lab.l_result_num is not None:
            result_num = float(lab.l_result_num)
        elif lab.l_result:
            try:
                result_num = float(str(lab.l_result).replace(",", "."))
            except (ValueError, AttributeError):
                result_text = lab.l_result

        if lab.l_test_id and (result_num is not None or result_text):
            test_ranges = ranges_by_test.get(lab.l_test_id, [])
            range_type, ref_min, ref_max = evaluate_reference_range_sync(
                test_ranges, result_num, patient_dob, patient_sex, result_text=result_text
            )

        lab.__dict__["range_type"] = range_type
        lab.__dict__["value_range_reference_min"] = float(ref_min) if ref_min is not None else None
        lab.__dict__["value_range_reference_max"] = float(ref_max) if ref_max is not None else None

        if lab.l_result_graphic:
            lab.l_result_graphic = get_graphic_url(lab.l_result_graphic)

        lab.__dict__["formats_complete"] = [
            link.format_complete.fc_name
            for link in formats_by_test.get(lab.l_test_id, [])
            if link.format_complete
        ]

    # Cargar sede
    headquarter = None
    if order.o_headquarter_id:
        headquarter = await db.get(Headquarter, order.o_headquarter_id)

    # Consultar InvoiceDetail directamente por orden, sin depender de labs
    study_invoice_value: dict[int, object] = {}
    invoice_summary: dict = {}

    inv_detail_result = await db.execute(
        select(InvoiceDetail)
        .join(OrdersDetail, InvoiceDetail.invd_order_detail_id == OrdersDetail.od_id)
        .where(OrdersDetail.od_order_id == o_id)
    )
    inv_details = inv_detail_result.scalars().all()

    for inv_det in inv_details:
        if inv_det.invd_study_id and inv_det.invd_study_id not in study_invoice_value:
            study_invoice_value[inv_det.invd_study_id] = inv_det.invd_value

    # Obtener el encabezado de la factura directamente desde Invoices
    invoice_ids = list({d.invd_invoice_id for d in inv_details if d.invd_invoice_id})
    if invoice_ids:
        inv_result = await db.execute(
            select(Invoice).where(Invoice.inv_id.in_(invoice_ids)).limit(1)
        )
        inv = inv_result.scalars().first()
        if inv:
            invoice_summary = {
                "inv_id": inv.inv_id,
                "inv_number": inv.inv_number,
                "inv_subtotal": float(inv.inv_subtotal) if inv.inv_subtotal is not None else None,
                "inv_tax": float(inv.inv_tax) if inv.inv_tax is not None else None,
                "inv_total": float(inv.inv_total) if inv.inv_total is not None else None,
                "inv_state": inv.inv_state,
                "inv_state_name": INVOICE_STATES.get(inv.inv_state) if inv.inv_state is not None else None,
                "inv_type": inv.inv_type,
                "inv_type_name": INVOICE_TYPES.get(inv.inv_type) if inv.inv_type is not None else None,
                "inv_sub_type_invoice": inv.inv_sub_type_invoice,
                "inv_sub_type_name": INVOICE_SUB_TYPES.get(inv.inv_sub_type_invoice) if inv.inv_sub_type_invoice is not None else None,
            }

    # Agrupar laboratories por estudio y obtener study_ids únicos
    from collections import defaultdict
    study_map = {}
    study_order = []
    unique_study_ids_in_order: list[int] = []

    # Pre-populate study_map from all OrdersDetails ordered by study order_of_print
    seen_od_study_ids: set[int] = set()
    sorted_details = sorted(
        order.details,
        key=lambda d: (d.study.order_of_print if d.study and d.study.order_of_print is not None else float("inf")),
    )
    for detail in sorted_details:
        study = detail.study
        study_id = study.id if study else 0
        if study_id not in seen_od_study_ids:
            seen_od_study_ids.add(study_id)
            od_cancelled = detail.od_cancelled if detail.od_cancelled is not None else 0
            study_map[study_id] = {
                "study_id": study_id,
                "study_name": study.name if study else None,
                "study_code": study.code if study else None,
                "study_value": study_invoice_value.get(study_id),
                "od_cancelled": od_cancelled,
                "laboratories": [],
            }
            study_order.append(study_id)
            if study_id and study_invoice_value.get(study_id) is None:
                unique_study_ids_in_order.append(study_id)

    # Attach laboratories to their study
    for lab in labs:
        study = lab.order_detail.study if lab.order_detail else None
        study_id = study.id if study else 0
        if study_id in study_map:
            study_map[study_id]["laboratories"].append(lab)

    # Load required test config per study to compute study state
    all_study_ids = [sid for sid in study_order if sid]
    required_tests_by_study: dict[int, set[int]] = {}
    if all_study_ids:
        std_result = await db.execute(
            select(StudiesTestDetail).where(
                StudiesTestDetail.studies_id.in_(all_study_ids),
                StudiesTestDetail.is_required == True,
            )
        )
        for std in std_result.scalars().all():
            required_tests_by_study.setdefault(std.studies_id, set()).add(std.tests_id)

    # Compute state per study based on labs with required tests
    STUDY_STATE_PENDIENTE = "Pendiente"
    STUDY_STATE_CON_RESULTADOS = "Con Resultados"
    STUDY_STATE_SIN_RESULTADOS = "Sin Resultados"
    STATES_WITH_RESULTS = { 3, 4}  # Con Resultados, Validada, Impreso

    for study_id, entry in study_map.items():
        required_test_ids = required_tests_by_study.get(study_id, set())
        study_labs = entry["laboratories"]
        labs_by_test: dict[int, int] = {
            lab.l_test_id: lab.l_state for lab in study_labs if lab.l_test_id is not None
        }

        if not required_test_ids:
            # No required tests defined: use lab states as-is
            if not study_labs:
                entry["study_state"] = STUDY_STATE_SIN_RESULTADOS
            elif all(labs_by_test.get(tid, 0) in STATES_WITH_RESULTS for tid in labs_by_test):
                entry["study_state"] = STUDY_STATE_CON_RESULTADOS
            else:
                entry["study_state"] = STUDY_STATE_PENDIENTE
        else:
            # Only required tests determine the state
            required_with_results = all(
                labs_by_test.get(tid, 0) in STATES_WITH_RESULTS
                for tid in required_test_ids
            )
            if required_with_results:
                entry["study_state"] = STUDY_STATE_CON_RESULTADOS
            elif any(
                labs_by_test.get(tid, 0) not in STATES_WITH_RESULTS
                for tid in required_test_ids
            ):
                entry["study_state"] = STUDY_STATE_PENDIENTE
            else:
                entry["study_state"] = STUDY_STATE_SIN_RESULTADOS

    # Fallback: si algún estudio no tiene valor desde InvoicesDetail, buscarlo en TariffsDetail
    tariff_id = order.o_tariff_id if hasattr(order, "o_tariff_id") else None
    if tariff_id and unique_study_ids_in_order:
        td_result = await db.execute(
            select(TariffDetail).filter(
                TariffDetail.td_tariff_id == tariff_id,
                TariffDetail.td_studie_id.in_(unique_study_ids_in_order),
            )
        )
        for td in td_result.scalars().all():
            if td.td_studie_id in study_map and study_map[td.td_studie_id]["study_value"] is None:
                study_map[td.td_studie_id]["study_value"] = td.td_value

    return {
        "order": order,
        "patient": order.patient,
        "headquarter": headquarter,
        "studies": [study_map[sid] for sid in study_order],
        "samples": samples,
        "invoice": invoice_summary if invoice_summary else None,
    }


async def edit_order(db: AsyncSession, o_id: int, data: dict, user_id: int | None = None):
    """
    Edita los campos permitidos de una orden y/o agrega nuevos estudios.

    - Actualiza: o_enterprise_id, o_diagnoses_id, o_service_id, o_autorizacion,
      o_pregnated, o_week_pregnated, o_priority, o_scholarity, o_note, o_tariff_id.
    - Si se envían estudios, valida que cada estudio exista en la tarifa vigente
      (o_tariff_id del request o el de la orden en BD). Los estudios ya presentes
      en la orden se omiten sin error.
    """
    try:
        studies_to_add: list[int] = data.pop("studies", None) or []

        # 1. Obtener la orden actual
        order = await db.get(Order, o_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada.")

        # --- Snapshot BEFORE changes ---
        from app.domains.traces.constants import OPERATION_EDIT_DEMOGRAPHICS
        from app.domains.traces.models import AppTrace

        editable_fields = [
            "o_enterprise_id", "o_diagnoses_id", "o_service_id", "o_autorizacion",
            "o_pregnated", "o_week_pregnated", "o_priority", "o_scholarity",
            "o_note", "o_tariff_id",
        ]

        field_labels = {
            "o_enterprise_id": "Empresa",
            "o_diagnoses_id": "Diagnóstico",
            "o_service_id": "Servicio",
            "o_autorizacion": "Autorización",
            "o_pregnated": "Embarazo",
            "o_week_pregnated": "Semanas embarazo",
            "o_priority": "Prioridad",
            "o_scholarity": "Escolaridad",
            "o_note": "Nota",
            "o_tariff_id": "Tarifa",
        }

        before_snapshot = {
            field: getattr(order, field, None)
            for field in editable_fields
        }

        # 2. Actualizar campos editables (solo los enviados)
        updated_fields: list[str] = []
        for field in editable_fields:
            if field in data and data[field] is not None:
                setattr(order, field, data[field])
                updated_fields.append(field)

        # --- Build diff description ---
        diff_parts: list[str] = []
        for field in updated_fields:
            label = field_labels.get(field, field)
            old_val = before_snapshot.get(field)
            new_val = data[field]
            diff_parts.append(f"{label}: {old_val} → {new_val}")

        await db.flush()

        # 3. Procesar estudios si se enviaron
        added_studies: list[int] = []
        skipped_studies: list[int] = []
        invalid_studies: list[int] = []
        study_od_map: dict[int, int] = {}

        # Buscar la factura existente asociada a la orden
        invoice: Invoice | None = None
        existing_inv_detail_result = await db.execute(
            select(InvoiceDetail)
            .join(OrdersDetail, InvoiceDetail.invd_order_detail_id == OrdersDetail.od_id)
            .where(OrdersDetail.od_order_id == o_id)
            .limit(1)
        )
        existing_inv_detail = existing_inv_detail_result.scalars().first()
        if existing_inv_detail:
            invoice = await db.get(Invoice, existing_inv_detail.invd_invoice_id)

        if studies_to_add:
            # Tarifa efectiva: la del request (ya aplicada) o la de la orden
            effective_tariff_id: int | None = data.get("o_tariff_id") or order.o_tariff_id

            if not effective_tariff_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La orden no tiene una tarifa asignada. Asigne una tarifa antes de agregar estudios."
                )

            # Estudios válidos en la tarifa
            tariff_study_ids = await OrderRepository.get_study_ids_for_tariff(db, effective_tariff_id)

            # Estudios ya existentes en la orden
            existing_study_ids = await OrderRepository.get_existing_study_ids_for_order(db, o_id)

            for study_id in studies_to_add:
                if study_id not in tariff_study_ids:
                    invalid_studies.append(study_id)
                    continue

                if study_id in existing_study_ids:
                    skipped_studies.append(study_id)
                    continue

                # Obtener configuración de pruebas del estudio
                stmt = (
                    select(StudiesTestDetail)
                    .filter(StudiesTestDetail.studies_id == study_id)
                    .options(selectinload(StudiesTestDetail.test))
                )
                result = await db.execute(stmt)
                test_links = result.scalars().all()

                if not test_links:
                    invalid_studies.append(study_id)
                    continue

                new_sample_types: set[int] = set()
                for link in test_links:
                    order_detail = OrdersDetail(
                        od_order_id=o_id,
                        od_study_id=study_id,
                        od_state=ORDER_DETAIL_STATE_INGRESADO,
                    )
                    db.add(order_detail)
                    await db.flush()

                    # Registrar el primer od_id de este estudio para InvoiceDetail
                    if study_id not in study_od_map:
                        study_od_map[study_id] = order_detail.od_id

                    blank_result = Laboratory(
                        l_order_detail_id=order_detail.od_id,
                        l_test_id=link.tests_id,
                        l_state=LABORATORY_STATE_SIN_RESULTADOS,
                    )
                    db.add(blank_result)

                    if link.test and link.test.samples_type_id:
                        new_sample_types.add(link.test.samples_type_id)

                # Agregar muestras nuevas si el sufijo no existe ya en la orden
                # (dos SampleTypes con el mismo sufijo comparten el mismo barcode)
                seen_suffixes: set[int] = set()
                existing_samples = await db.execute(
                    select(SamplesOrder)
                    .where(SamplesOrder.so_order_id == o_id)
                    .options(selectinload(SamplesOrder.sample_type))
                )
                for existing in existing_samples.scalars().all():
                    st_type = existing.sample_type
                    if st_type and st_type.st_sufix is not None:
                        seen_suffixes.add(st_type.st_sufix)
                    elif st_type:
                        seen_suffixes.add(st_type.st_id)

                from app.domains.samples.domain.models import SampleType
                for st_id in new_sample_types:
                    sample_type = await db.get(SampleType, st_id)
                    st_sufix = (sample_type.st_sufix if sample_type and sample_type.st_sufix is not None else st_id)
                    if st_sufix not in seen_suffixes:
                        seen_suffixes.add(st_sufix)
                        db.add(SamplesOrder(
                            so_order_id=o_id,
                            so_sample_type_id=st_id,
                            so_barcode=f"{order.o_number}{st_sufix}",
                            so_state=1,
                        ))

                added_studies.append(study_id)
                existing_study_ids.add(study_id)

        # 4. Crear InvoiceDetail y actualizar totales de la factura para nuevos estudios
        if added_studies and invoice:
            effective_tariff = data.get("o_tariff_id") or order.o_tariff_id
            additional = Decimal(0)
            for study_id in added_studies:
                td_value = None
                if effective_tariff:
                    td_res = await db.execute(
                        select(TariffDetail).filter(
                            TariffDetail.td_tariff_id == effective_tariff,
                            TariffDetail.td_studie_id == study_id,
                        )
                    )
                    td = td_res.scalars().first()
                    if td:
                        td_value = td.td_value
                inv_det = InvoiceDetail(
                    invd_invoice_id=invoice.inv_id,
                    invd_order_detail_id=study_od_map.get(study_id),
                    invd_study_id=study_id,
                    invd_value=td_value,
                    invd_discount=None,
                    invd_total=td_value,
                    invd_created_by=data.get("o_AppUser_id"),
                )
                db.add(inv_det)
                if td_value is not None:
                    additional += Decimal(str(td_value))
            if additional:
                invoice.inv_subtotal = (Decimal(str(invoice.inv_subtotal)) if invoice.inv_subtotal else Decimal(0)) + additional
                invoice.inv_total = (Decimal(str(invoice.inv_total)) if invoice.inv_total else Decimal(0)) + additional

        # 5. Registrar trazas en AppTrace (ANTES del commit)
        # 5a. Demográficos modificados
        if diff_parts and user_id:
            db.add(AppTrace(
                usr_id=user_id,
                order_id=o_id,
                operation_type=OPERATION_EDIT_DEMOGRAPHICS,
                operation_description=f"Edición de orden {order.o_number}",
                notes=" | ".join(diff_parts) if diff_parts else None,
            ))

        # 5b. Estudios agregados
        if added_studies and user_id:
            studies_result = await db.execute(
                select(StudiesLab.id, StudiesLab.code, StudiesLab.name)
                .where(StudiesLab.id.in_(added_studies))
            )
            study_info = {row.id: f"{row.code} - {row.name}" for row in studies_result.all()}
            for study_id in added_studies:
                info = study_info.get(study_id, f"ID {study_id}")
                db.add(AppTrace(
                    usr_id=user_id,
                    order_id=o_id,
                    operation_type=OPERATION_CREATE_ORDER,
                    operation_description=f"Adición estudio a orden {order.o_number}",
                    notes=f"Estudio agregado: {info}",
                ))

        await db.commit()

        # Construir mensaje
        parts: list[str] = []
        if updated_fields:
            parts.append(f"Campos actualizados: {', '.join(updated_fields)}.")
        if added_studies:
            parts.append(f"Estudios agregados: {added_studies}.")
        if skipped_studies:
            parts.append(f"Estudios omitidos (ya existían): {skipped_studies}.")
        if invalid_studies:
            parts.append(f"Estudios no válidos en la tarifa: {invalid_studies}.")
        if not parts:
            parts.append("No se realizaron cambios.")

        return {
            "success": True,
            "o_id": o_id,
            "updated_fields": updated_fields,
            "added_studies": added_studies,
            "skipped_studies": skipped_studies,
            "invalid_studies": invalid_studies,
            "message": " ".join(parts),
        }

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de integridad al editar la orden: {str(e.orig)}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al editar la orden: {str(e)}"
        )


async def get_grafico_evolutivo(
    db: AsyncSession,
    patient_id: int,
    test_id: int,
):
    """
    Devuelve el histórico de resultados de un test para un paciente dado,
    con evaluación de rango de referencia por cada resultado.
    """
    from app.domains.patients.domain.models import Patient

    # 1. Obtener paciente
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    # 2. Obtener test
    test = await db.get(TestsLab, test_id)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prueba de laboratorio no encontrada.")

    # 3. Consultar histórico: Orders → OrdersDetails → Laboratories para este paciente+test
    #    Solo órdenes con o_order_state in (3,4) y laboratorios con l_state in (2,3,4)
    stmt = (
        select(Laboratory, Order)
        .join(OrdersDetail, Laboratory.l_order_detail_id == OrdersDetail.od_id)
        .join(Order, OrdersDetail.od_order_id == Order.o_id)
        .where(
            Order.o_his_id == patient_id,
            Laboratory.l_test_id == test_id,
            Order.o_order_state.in_([3, 4]),
            Laboratory.l_state.in_([2, 3, 4]),
        )
        .order_by(Order.o_date.asc(), Order.o_id.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    patient_dob = getattr(patient, "pt_date_of_birth", None)
    patient_sex = getattr(patient, "pt_sex_type", None)

    # Nombre del paciente
    nombre_parts = [
        getattr(patient, "pt_firts_name", "") or "",
        getattr(patient, "pt_middle_name", "") or "",
        getattr(patient, "pt_last_name", "") or "",
        getattr(patient, "pt_second_last_name", "") or "",
    ]
    nombre_paciente = " ".join(p.strip() for p in nombre_parts if p.strip())

    historico = []
    decimals = test.num_decimal_result
    for lab, order in rows:
        # Obtener valor numérico o textual
        result_num = None
        result_text = None
        if lab.l_result_num is not None:
            result_num = float(lab.l_result_num)
            if decimals is not None:
                result_num = round(result_num, decimals)
        elif lab.l_result:
            try:
                result_num = float(str(lab.l_result).replace(",", "."))
                if decimals is not None:
                    result_num = round(result_num, decimals)
            except (ValueError, AttributeError):
                result_text = lab.l_result

        # Evaluar rango de referencia
        range_type, ref_min, ref_max = await evaluate_reference_range(
            db,
            test_id,
            result_num,
            patient_dob,
            patient_sex,
            result_text=result_text,
        )

        # Fecha del resultado: preferir l_date_transmited, luego l_created_at
        from datetime import datetime as dt
        fecha = lab.l_date_transmited or lab.l_created_at
        if fecha is None and order.o_date:
            fecha = dt.combine(order.o_date, dt.min.time())

        historico.append({
            "fecha": fecha,
            "valor": result_num if result_num is not None else result_text,
            "referencia_min": float(ref_min) if ref_min is not None else None,
            "referencia_max": float(ref_max) if ref_max is not None else None,
            "estado": range_type,
            "orden_numero": order.o_number,
        })

    return {
        "prueba": test.name,
        "codigo": test.code,
        "unidad": test.units,
        "paciente": nombre_paciente,
        "historico": historico,
    }


async def _compute_orders_state(db: AsyncSession, order_ids: list[int]) -> dict[int, int]:
    """
    Calcula el o_order_state de una lista de órdenes basándose en la configuración
    is_required de StudiesTestDetail.

    Para cada orden:
      - Se consultan los laboratorios (agrupados por estudio y test).
      - Se carga la configuración de pruebas requeridas (is_required=True) por estudio.
      - Si un estudio tiene pruebas requeridas, solo esas determinan si el estudio
        está completado (todas con l_state en {2,3,4}).
      - Si el estudio no tiene pruebas requeridas definidas, se usa el comportamiento
        legacy: el estudio está completado si todas sus pruebas tienen resultado.
      - La orden está "Con Resultados" (3) solo si TODOS sus estudios están completados.
      - En cualquier otro caso, la orden está "Pendiente" (2).

    Retorna un diccionario {order_id: o_order_state}.
    """
    from app.domains.laboratories.domain.constants import (
        LABORATORY_STATE_CON_RESULTADOS,
        LABORATORY_STATE_VALIDADA,
        LABORATORY_STATE_IMPRESO,
    )
    from app.domains.orders.domain.constants import ORDER_STATE_PENDIENTE, ORDER_STATE_CON_RESULTADOS

    LAB_STATES_WITH_RESULTS = {
        LABORATORY_STATE_CON_RESULTADOS,
        LABORATORY_STATE_VALIDADA,
        LABORATORY_STATE_IMPRESO,  # 2, 3, 4
    }

    if not order_ids:
        return {}

    # 1. Obtener todos los labs de las órdenes consultadas
    stmt_labs = (
        select(
            Laboratory.l_state,
            OrdersDetail.od_order_id,
            OrdersDetail.od_study_id,
            Laboratory.l_test_id,
        )
        .join(OrdersDetail, Laboratory.l_order_detail_id == OrdersDetail.od_id)
        .where(OrdersDetail.od_order_id.in_(order_ids))
    )
    result_labs = await db.execute(stmt_labs)
    labs_data = result_labs.all()

    # 2. Obtener todos los study_ids únicos de esas órdenes
    all_study_ids = list({row.od_study_id for row in labs_data if row.od_study_id})

    # 3. Cargar is_required config para esos estudios
    required_tests_by_study: dict[int, set[int]] = {}
    if all_study_ids:
        std_result = await db.execute(
            select(StudiesTestDetail).where(
                StudiesTestDetail.studies_id.in_(all_study_ids),
                StudiesTestDetail.is_required == True,
            )
        )
        for std in std_result.scalars().all():
            required_tests_by_study.setdefault(std.studies_id, set()).add(std.tests_id)

    # 4. Agrupar labs por orden y estudio:
    #    {order_id: {study_id: {test_id: l_state}}}
    order_labs: dict[int, dict[int, dict[int, int]]] = {}
    for row in labs_data:
        oid = row.od_order_id
        sid = row.od_study_id
        tid = row.l_test_id
        state = row.l_state

        if oid not in order_labs:
            order_labs[oid] = {}
        if sid not in order_labs[oid]:
            order_labs[oid][sid] = {}
        if tid is not None:
            order_labs[oid][sid][tid] = state

    # 5. Evaluar cada orden
    result: dict[int, int] = {}
    for oid in order_ids:
        studies = order_labs.get(oid, {})
        if not studies:
            result[oid] = ORDER_STATE_PENDIENTE
            continue

        all_studies_done = True
        for study_id, tests_map in studies.items():
            required_ids = required_tests_by_study.get(study_id, set())
            if not required_ids:
                # Sin required: el estudio está completo si todas sus pruebas tienen resultado
                if not all(state in LAB_STATES_WITH_RESULTS for state in tests_map.values()):
                    all_studies_done = False
                    break
            else:
                # Solo las requeridas determinan el estado
                all_required_have_results = all(
                    tests_map.get(tid, 0) in LAB_STATES_WITH_RESULTS
                    for tid in required_ids
                )
                if not all_required_have_results:
                    all_studies_done = False
                    break

        result[oid] = ORDER_STATE_CON_RESULTADOS if all_studies_done else ORDER_STATE_PENDIENTE

    return result


async def filter_orders(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    order_states: Optional[list[int]] = None,
    work_group_ids: Optional[list[int]] = None,
    study_ids: Optional[list[int]] = None,
) -> list[dict]:
    """
    Filtra órdenes por múltiples criterios y retorna una lista plana
    con los campos especificados: o_id, o_number, pt_name, pt_number_document.
    """
    orders = await OrderRepository.get_filtered_orders(
        db,
        start_date=start_date,
        end_date=end_date,
        order_states=order_states,
        work_group_ids=work_group_ids,
        study_ids=study_ids,
    )

    result = []
    for order in orders:
        patient = order.patient
        pt_name = ""
        pt_number_document = ""
        if patient:
            parts = [
                patient.pt_firts_name,
                patient.pt_middle_name,
                patient.pt_last_name,
                patient.pt_second_last_name,
            ]
            pt_name = " ".join(part for part in parts if part)
            pt_number_document = patient.pt_Number_document or ""

        result.append({
            "o_id": order.o_id,
            "o_number": order.o_number,
            "pt_name": pt_name,
            "pt_number_document": pt_number_document,
        })

    return result

from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.orders.infrastructure.repository import OrderRepository
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.shared.utils.range_evaluator import evaluate_reference_range

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.orders.domain.constants import ORDER_STATE_INGRESADA, ORDER_DETAIL_STATE_INGRESADO
from app.domains.laboratories.domain.constants import LABORATORY_STATE_SIN_RESULTADOS
from app.domains.samples.domain.models import SamplesOrder
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

        order = await OrderRepository.create(db, data)
        await db.flush() # Obtenemos o_id sin confirmar la transacción todavía        
        # Diccionario para evitar duplicar tipos de muestra en una misma orden
        unique_sample_types = set()
        # Mapa study_id → primer od_id creado (para InvoiceDetail)
        study_od_map: dict[int, int] = {}

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

            # 3. Crear un OrdersDetail y un Laboratory por cada prueba del estudio
            for link in test_links:
                order_detail = OrdersDetail(
                    od_order_id=order.o_id,
                    od_study_id=study_id,
                    od_state=ORDER_DETAIL_STATE_INGRESADO
                )
                db.add(order_detail)
                await db.flush()  # Para obtener od_id

                # Registrar el primer od_id de este estudio para la factura
                if study_id not in study_od_map:
                    study_od_map[study_id] = order_detail.od_id

                blank_result = Laboratory(
                    l_order_detail_id=order_detail.od_id,
                    l_test_id=link.tests_id,
                    l_state=LABORATORY_STATE_SIN_RESULTADOS
                )
                db.add(blank_result)

                # 4. Recolectar tipos de muestra para SamplesOrder
                if link.test and link.test.samples_type_id:
                    unique_sample_types.add(link.test.samples_type_id)

        # 6. Generar automáticamente registros de muestras (SamplesOrder)
        for st_id in unique_sample_types:
            sample_order = SamplesOrder(
                so_order_id=order.o_id,
                so_sample_type_id=st_id,
                so_barcode=f"{order.o_number}-{st_id}", # Generación simple de código de barras
                so_state=1, # Estado: Generado
                so_number_studies=len(studies_ids) # Opcional: conteo de estudios vinculados
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

async def list_orders(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None):
    items, total = await OrderRepository.get_paginated(db, skip, limit, search)
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
        
    # 2. Consultar laboratorios paginados
    labs, total_labs = await OrderRepository.get_laboratories_paginated(db, order.o_id, skip_labs, limit_labs)
    
    # 3. Consultar pruebas (TestsLab) paginadas
    tests, total_tests = await OrderRepository.get_tests_paginated(db, order.o_id, skip_tests, limit_tests)

    # 4. Enriquecer laboratorios con rangos de referencia
    patient = order.patient
    patient_dob = getattr(patient, "pt_date_of_birth", None) if patient else None
    patient_sex = getattr(patient, "pt_sex_type", None) if patient else None

    enriched_labs = []
    for lab in labs:
        range_type, ref_min, ref_max = (None, None, None)
        # Obtener valor numérico y textual para evaluación
        result_num = None
        result_text = None
        if lab.l_result_num is not None:
            result_num = float(lab.l_result_num)
        elif lab.l_result:
            # Intentar parsear como número (fallback por si l_result_num no está poblado)
            try:
                result_num = float(str(lab.l_result).replace(",", "."))
            except (ValueError, AttributeError):
                # Es texto puro
                result_text = lab.l_result

        if lab.l_test_id and (result_num is not None or result_text):
            range_type, ref_min, ref_max = await evaluate_reference_range(
                db,
                lab.l_test_id,
                result_num,
                patient_dob,
                patient_sex,
                result_text=result_text,
            )
        # Attach campos extra como atributos transitorios para que Pydantic los serialice
        lab.__dict__["range_type"] = range_type
        lab.__dict__["value_range_reference_min"] = float(ref_min) if ref_min is not None else None
        lab.__dict__["value_range_reference_max"] = float(ref_max) if ref_max is not None else None
        enriched_labs.append(lab)

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
            "items": tests
        }
    }

async def get_full_order_details_by_id(db: AsyncSession, o_id: int):
    # Sin paginación
    order = await OrderRepository.get_by_id(db, o_id) # Carga relaciones: patient, service, diagnosis, enterprise, schooling, tariff, details→study
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")
        
    labs, _ = await OrderRepository.get_laboratories_paginated(db, order.o_id, 0, 10000)
    tests, _ = await OrderRepository.get_tests_paginated(db, order.o_id, 0, 10000)
    samples = await OrderRepository.get_samples_by_order_id(db, order.o_id)

    # Cargar sede
    headquarter = None
    if order.o_headquarter_id:
        headquarter = await db.get(Headquarter, order.o_headquarter_id)

    # Obtener los od_id de esta orden para buscar los valores en InvoicesDetail
    od_ids = [lab.order_detail.od_id for lab in labs if lab.order_detail]
    study_invoice_value: dict[int, object] = {}
    invoice_summary: dict = {}

    if od_ids:
        inv_detail_result = await db.execute(
            select(InvoiceDetail).where(InvoiceDetail.invd_order_detail_id.in_(od_ids))
        )
        inv_details = inv_detail_result.scalars().all()

        for inv_det in inv_details:
            if inv_det.invd_study_id and inv_det.invd_study_id not in study_invoice_value:
                study_invoice_value[inv_det.invd_study_id] = inv_det.invd_value

        # Obtener el encabezado de la factura para el resumen
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
                    "inv_subtotal": inv.inv_subtotal,
                    "inv_tax": inv.inv_tax,
                    "inv_total": inv.inv_total,
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
    for lab in labs:
        study = lab.order_detail.study if lab.order_detail else None
        study_id = study.id if study else 0
        if study_id not in study_map:
            study_map[study_id] = {
                "study_id": study_id,
                "study_name": study.name if study else None,
                "study_code": study.code if study else None,
                "study_value": study_invoice_value.get(study_id),
                "laboratories": [],
            }
            study_order.append(study_id)
            if study_id and study_invoice_value.get(study_id) is None:
                unique_study_ids_in_order.append(study_id)
        study_map[study_id]["laboratories"].append(lab)

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
        "laboratories_by_study": [study_map[sid] for sid in study_order],
        "tests": tests,
        "samples": samples,
        "invoice": invoice_summary if invoice_summary else None,
    }


async def edit_order(db: AsyncSession, o_id: int, data: dict):
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

        # 2. Actualizar campos editables (solo los enviados)
        editable_fields = [
            "o_enterprise_id", "o_diagnoses_id", "o_service_id", "o_autorizacion",
            "o_pregnated", "o_week_pregnated", "o_priority", "o_scholarity",
            "o_note", "o_tariff_id",
        ]
        updated_fields: list[str] = []
        for field in editable_fields:
            if field in data and data[field] is not None:
                setattr(order, field, data[field])
                updated_fields.append(field)

        await db.flush()

        # 3. Procesar estudios si se enviaron
        added_studies: list[int] = []
        skipped_studies: list[int] = []
        invalid_studies: list[int] = []

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

                    blank_result = Laboratory(
                        l_order_detail_id=order_detail.od_id,
                        l_test_id=link.tests_id,
                        l_state=LABORATORY_STATE_SIN_RESULTADOS,
                    )
                    db.add(blank_result)

                    if link.test and link.test.samples_type_id:
                        new_sample_types.add(link.test.samples_type_id)

                # Agregar muestras nuevas si el tipo no existe ya en la orden
                for st_id in new_sample_types:
                    from app.domains.samples.domain.models import SamplesOrder
                    existing_sample = await db.execute(
                        select(SamplesOrder).where(
                            SamplesOrder.so_order_id == o_id,
                            SamplesOrder.so_sample_type_id == st_id,
                        )
                    )
                    if not existing_sample.scalar_one_or_none():
                        db.add(SamplesOrder(
                            so_order_id=o_id,
                            so_sample_type_id=st_id,
                            so_barcode=f"{order.o_number}-{st_id}",
                            so_state=1,
                        ))

                added_studies.append(study_id)
                existing_study_ids.add(study_id)

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
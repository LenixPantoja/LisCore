from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from datetime import datetime

from app.domains.requests.api.schemas import (
    InboundOrderCreate,
    InboundOrderUpdate,
    InboundOrderDetailUpdate,
    InboundOrderResponse,
    CreateOrderFromInboundRequest,
    CreateOrderFromInboundResponse,
)
from app.domains.requests.infrastructure.repository import (
    InboundOrderRepository,
    InboundOrderDetailRepository,
)
from app.domains.requests.domain.models import InboundOrderDetail
from app.domains.requests.domain.constants import INBOUND_ORDER_DETAIL_STATE_EJECUTADA


async def create_inbound_order(db: AsyncSession, payload: InboundOrderCreate):
    order_data = payload.model_dump(exclude={"details"})
    details_data = [d.model_dump() for d in payload.details]
    order = await InboundOrderRepository.create(db, order_data, details_data)
    return InboundOrderResponse.from_orm_with_names(order)


async def get_inbound_order(db: AsyncSession, io_id: int):
    order = await InboundOrderRepository.get_by_id(db, io_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Solicitud entrante con ID {io_id} no encontrada.",
        )
    return InboundOrderResponse.from_orm_with_names(order)


async def list_inbound_orders(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    detail_states: Optional[list[int]] = None,
    enterprise_id: int = 0,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
):
    skip = (page - 1) * page_size
    total, items = await InboundOrderRepository.get_paginated(
        db,
        skip=skip,
        limit=page_size,
        detail_states=detail_states,
        enterprise_id=enterprise_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [InboundOrderResponse.from_orm_with_names(o) for o in items],
    }


async def update_inbound_order(db: AsyncSession, io_id: int, payload: InboundOrderUpdate):
    await get_inbound_order(db, io_id)  # valida existencia
    data = payload.model_dump(exclude_none=True)
    order = await InboundOrderRepository.update(db, io_id, data)
    return InboundOrderResponse.from_orm_with_names(order)


async def delete_inbound_order(db: AsyncSession, io_id: int):
    await get_inbound_order(db, io_id)  # valida existencia
    await InboundOrderRepository.delete(db, io_id)


async def update_inbound_order_detail(db: AsyncSession, iod_id: int, payload: InboundOrderDetailUpdate):
    detail = await InboundOrderDetailRepository.get_by_id(db, iod_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detalle con ID {iod_id} no encontrado.",
        )
    data = payload.model_dump(exclude_none=True)
    return await InboundOrderDetailRepository.update(db, iod_id, data)


async def create_order_from_inbound(
    db: AsyncSession,
    payload: CreateOrderFromInboundRequest,
) -> CreateOrderFromInboundResponse:
    """
    Crea una Order en el sistema a partir de un InboundOrder y los
    InboundOrderDetail seleccionados. Después actualiza esos detalles
    con estado Ejecutada y el id de la orden creada.
    """
    from app.domains.orders.application.use_cases.order_use_cases import create_order

    # 1. Cargar el InboundOrder con sus relaciones básicas
    inbound = await InboundOrderRepository.get_by_id(db, payload.inbound_order_id)
    if not inbound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"InboundOrder con ID {payload.inbound_order_id} no encontrado.",
        )

    # 2. Cargar los detalles seleccionados con su relación de estudio
    from sqlalchemy.orm import selectinload as _selectinload
    result = await db.execute(
        select(InboundOrderDetail)
        .where(
            InboundOrderDetail.iod_id.in_(payload.inbound_detail_ids),
            InboundOrderDetail.iod_inboundOrder_id == payload.inbound_order_id,
        )
        .options(_selectinload(InboundOrderDetail.study))
    )
    selected_details = result.scalars().all()

    if not selected_details:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontraron detalles válidos para el InboundOrder especificado.",
        )

    # Validar que ningún detalle esté ya en estado Ejecutada
    already_executed = [
        d for d in selected_details
        if d.iod_state == INBOUND_ORDER_DETAIL_STATE_EJECUTADA
    ]
    if already_executed:
        executed_info = [
            f"{d.study.name} ({d.study.code})" if d.study else f"Detalle {d.iod_id}"
            for d in already_executed
        ]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Los siguientes estudios ya fueron ejecutados y no pueden registrarse nuevamente: {'; '.join(executed_info)}",
        )

    study_ids = [d.iod_study_id for d in selected_details if d.iod_study_id]

    if not study_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los detalles seleccionados no tienen estudios asociados.",
        )

    # Validar que todos los estudios tengan pruebas configuradas
    from app.domains.studieslab.infrastructure.repository import StudiesLabRepository
    studies_without_tests = await StudiesLabRepository.get_studies_without_tests(db, study_ids)
    if studies_without_tests:
        study_name_map = {
            d.iod_study_id: (d.study.name if d.study else f"ID {d.iod_study_id}")
            for d in selected_details
        }
        names = [study_name_map.get(sid, f"ID {sid}") for sid in studies_without_tests]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Los siguientes estudios no tienen pruebas configuradas: {', '.join(names)}",
        )

    # 3. Calcular la edad del paciente en formato "Xa Ym Zd"
    patient = inbound.patient
    o_age: Optional[str] = None
    if patient and patient.pt_date_of_birth:
        from app.domains.patients.domain.rules import calculate_age
        age_parts = calculate_age(patient.pt_date_of_birth)
        o_age = f"{age_parts['years']}a {age_parts['months']}m {age_parts['days']}d"

    # 4. Construir los datos de la orden mapeando campos del InboundOrder
    # El tariff_id del payload tiene prioridad; si no se envía, se usa el del InboundOrder
    effective_tariff_id = payload.tariff_id or inbound.io_tariff_id
    if not effective_tariff_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe indicar una tarifa (tariff_id) o asegurarse de que el InboundOrder tenga una tarifa asignada.",
        )

    order_data = {
        "o_his_id": inbound.io_patient_id,
        "o_age": o_age,
        "o_tariff_id": effective_tariff_id,
        "o_service_id": inbound.io_service_id,
        "o_diagnoses_id": inbound.io_diagnostic_id,
        "o_priority": inbound.io_priority or 0,
        "o_enterprise_id": inbound.io_enterprise_id,
        "o_scholarity": inbound.io_scholarity_id,
        "o_headquarter_id": payload.o_headquarter_id or inbound.io_headquarter_id,
        "o_AppUser_id": payload.o_AppUser_id,
        "o_autorizacion": inbound.io_number_request,
        "studies": study_ids,
    }

    # 4. Crear la orden (genera número, detalles, laboratorios, muestras, factura)
    order = await create_order(db, order_data)

    # 5. Mapear Laboratories creados a cada InboundOrderDetail
    #    Un InboundOrderDetail → un estudio (iod_study_id)
    #    Para cada estudio se crea al menos un OrdersDetail y sus Laboratories
    from sqlalchemy.orm import selectinload as _selectinload
    from app.domains.laboratories.domain.models import Laboratory as LabModel
    from app.domains.orders.domain.models import OrdersDetail as ODModel

    labs_result = await db.execute(
        select(LabModel)
        .join(ODModel, LabModel.l_order_detail_id == ODModel.od_id)
        .where(ODModel.od_order_id == order.o_id)
        .options(_selectinload(LabModel.order_detail))
    )
    all_labs: list = labs_result.scalars().all()

    # Agrupar laboratories por study_id: {study_id: [LabModel, ...]}
    labs_by_study: dict[int, list] = {}
    for lab in all_labs:
        study_id = lab.order_detail.od_study_id if lab.order_detail else None
        if study_id is not None:
            labs_by_study.setdefault(study_id, []).append(lab)

    # 6. Actualizar los InboundOrderDetail: estado Ejecutada + guardar o_id + iod_laboratory_id
    updated_ids: list[int] = []
    for detail in selected_details:
        detail.iod_state = INBOUND_ORDER_DETAIL_STATE_EJECUTADA
        detail.iod_order_id = order.o_id

        # Asignar el primer laboratory del estudio correspondiente
        study_labs = labs_by_study.get(detail.iod_study_id, [])
        if study_labs:
            detail.iod_laboratory_id = study_labs[0].l_id

        db.add(detail)
        updated_ids.append(detail.iod_id)

    await db.commit()

    return CreateOrderFromInboundResponse(
        o_id=order.o_id,
        o_number=order.o_number,
        inbound_order_id=payload.inbound_order_id,
        updated_detail_ids=updated_ids,
    )

from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.orders.infrastructure.repository import OrderRepository
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.samples.domain.models import SamplesOrder
from app.domains.laboratories.domain.models import Laboratory
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail
from app.domains.testslabs.domain.models import TestsLab
from utils.Consecutives.consecutive_orders import generate_order_number

async def create_order(db: AsyncSession, data: dict):
    studies_ids = data.pop("studies", [])
    if not studies_ids:
        raise HTTPException(status_code=400, detail="Debe solicitar al menos un estudio.")

    try:
        # 1. Crear el encabezado de la Orden
        # Generamos el número de orden automáticamente ignorando el del request
        data["o_number"] = await generate_order_number(db, data.get("o_date"))
        
        order = await OrderRepository.create(db, data)
        await db.flush() # Obtenemos o_id sin confirmar la transacción todavía
        
        # Diccionario para evitar duplicar tipos de muestra en una misma orden
        unique_sample_types = set()

        for study_id in studies_ids:
            # 2. Insertar en OrdersDetails
            order_detail = OrdersDetail(
                od_order_id=order.o_id,
                od_study_id=study_id,
                od_state=1 # Estado inicial: Pendiente
            )
            db.add(order_detail)
            await db.flush() # Para obtener od_id

            # 3. Consultar StudiesTestDetail para obtener las pruebas y tipos de muestra
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

            # 4. Generar registro en Laboratories (1:1 con OrdersDetail debido al UNIQUE)
            # Tomamos la primera prueba configurada para este estudio
            main_test = test_links[0]
            blank_result = Laboratory(
                l_order_detail_id=order_detail.od_id,
                l_test_id=main_test.tests_id,
                l_state=0 # Pendiente
            )
            db.add(blank_result)

            # 5. Recolectar tipos de muestra para SamplesOrder
            for link in test_links:
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
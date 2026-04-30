from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.requests.api.schemas import (
    InboundOrderCreate,
    InboundOrderUpdate,
    InboundOrderDetailUpdate,
)
from app.domains.requests.infrastructure.repository import (
    InboundOrderRepository,
    InboundOrderDetailRepository,
)


async def create_inbound_order(db: AsyncSession, payload: InboundOrderCreate):
    order_data = payload.model_dump(exclude={"details"})
    details_data = [d.model_dump() for d in payload.details]
    return await InboundOrderRepository.create(db, order_data, details_data)


async def get_inbound_order(db: AsyncSession, io_id: int):
    order = await InboundOrderRepository.get_by_id(db, io_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Solicitud entrante con ID {io_id} no encontrada.",
        )
    return order


async def list_inbound_orders(db: AsyncSession, page: int = 1, page_size: int = 20):
    skip = (page - 1) * page_size
    total, items = await InboundOrderRepository.get_paginated(db, skip=skip, limit=page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def update_inbound_order(db: AsyncSession, io_id: int, payload: InboundOrderUpdate):
    await get_inbound_order(db, io_id)  # valida existencia
    data = payload.model_dump(exclude_none=True)
    updated = await InboundOrderRepository.update(db, io_id, data)
    return updated


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

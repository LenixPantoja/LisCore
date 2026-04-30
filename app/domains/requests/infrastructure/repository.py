from typing import Optional
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.requests.domain.models import InboundOrder, InboundOrderDetail


class InboundOrderRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict, details: list[dict]) -> InboundOrder:
        now = datetime.utcnow()
        order = InboundOrder(**data, io_created_at=now, io_updated_at=now)
        db.add(order)
        await db.flush()

        for detail_data in details:
            detail = InboundOrderDetail(
                **detail_data,
                iod_inboundOrder_id=order.io_id,
                iod_created_at=now,
                iod_updated_at=now,
            )
            db.add(detail)

        await db.commit()
        await db.refresh(order)
        return await InboundOrderRepository.get_by_id(db, order.io_id)

    @staticmethod
    async def get_by_id(db: AsyncSession, io_id: int) -> Optional[InboundOrder]:
        result = await db.execute(
            select(InboundOrder)
            .filter(InboundOrder.io_id == io_id)
            .options(selectinload(InboundOrder.details))
        )
        return result.scalars().first()

    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[int, list[InboundOrder]]:
        total_result = await db.execute(select(func.count()).select_from(InboundOrder))
        total = total_result.scalar_one()

        result = await db.execute(
            select(InboundOrder)
            .options(selectinload(InboundOrder.details))
            .order_by(InboundOrder.io_id.desc())
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()
        return total, list(items)

    @staticmethod
    async def update(db: AsyncSession, io_id: int, data: dict) -> Optional[InboundOrder]:
        order = await InboundOrderRepository.get_by_id(db, io_id)
        if not order:
            return None

        data["io_updated_at"] = datetime.utcnow()
        for key, value in data.items():
            setattr(order, key, value)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def delete(db: AsyncSession, io_id: int) -> bool:
        order = await InboundOrderRepository.get_by_id(db, io_id)
        if not order:
            return False
        await db.delete(order)
        await db.commit()
        return True


class InboundOrderDetailRepository:

    @staticmethod
    async def get_by_id(db: AsyncSession, iod_id: int) -> Optional[InboundOrderDetail]:
        result = await db.execute(
            select(InboundOrderDetail).filter(InboundOrderDetail.iod_id == iod_id)
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, iod_id: int, data: dict) -> Optional[InboundOrderDetail]:
        detail = await InboundOrderDetailRepository.get_by_id(db, iod_id)
        if not detail:
            return None

        data["iod_updated_at"] = datetime.utcnow()
        for key, value in data.items():
            setattr(detail, key, value)

        await db.commit()
        await db.refresh(detail)
        return detail

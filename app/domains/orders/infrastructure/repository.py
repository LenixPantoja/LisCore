from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.domains.orders.domain.models import Order

class OrderRepository:
    @staticmethod
    async def create(db: AsyncSession, data: dict) -> Order:
        new_order = Order(**data)
        db.add(new_order)
        return new_order

    @staticmethod
    async def get_all(db: AsyncSession) -> List[Order]:
        result = await db.execute(
            select(Order).options(
                selectinload(Order.patient),
                selectinload(Order.service),
                selectinload(Order.diagnosis),
                selectinload(Order.enterprise),
                selectinload(Order.schooling),
                selectinload(Order.tariff)
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, o_id: int) -> Optional[Order]:
        result = await db.execute(
            select(Order).filter(Order.o_id == o_id).options(
                selectinload(Order.patient),
                selectinload(Order.service),
                selectinload(Order.diagnosis),
                selectinload(Order.enterprise),
                selectinload(Order.schooling),
                selectinload(Order.tariff)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, o_id: int, update_data: dict) -> Optional[Order]:
        order = await db.get(Order, o_id)
        if order:
            for key, value in update_data.items():
                setattr(order, key, value)
            await db.commit()
            await db.refresh(order)
        return order
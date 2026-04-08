from typing import List, Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.domains.orders.domain.models import Order

class OrderRepository:
    @staticmethod
    async def create(db: AsyncSession, data: dict) -> Order:
        new_order = Order(**data)
        db.add(new_order)
        return new_order

    @staticmethod
    async def get_paginated(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None
    ) -> Tuple[Sequence[Order], int]:
        # 1. Base query con relaciones
        query = select(Order).options(
            selectinload(Order.patient),
            selectinload(Order.service),
            selectinload(Order.diagnosis),
            selectinload(Order.enterprise),
            selectinload(Order.schooling),
            selectinload(Order.tariff)
        )

        # 2. Filtro de búsqueda por número de orden
        if search:
            query = query.filter(Order.o_number.ilike(f"%{search}%"))

        # 3. Conteo total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # 4. Resultados paginados
        result = await db.execute(query.offset(skip).limit(limit).order_by(Order.o_id.desc()))
        return result.scalars().all(), total

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
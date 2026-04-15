from typing import List, Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.domains.orders.domain.models import Order
from datetime import date

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

    @staticmethod
    async def get_next_order_number(db: AsyncSession) -> str:
        """
        Generate next order number based on format MMDDCCCCYY.
        
        Logic:
        1. Get last order's o_number
        2. Extract date parts (MM, DD, YY) and sequence (CCCC)
        3. If date matches today, increment sequence
        4. If date differs, reset sequence to 0001 with today's date
        """
        # Get today's date parts
        today = date.today()
        today_mm = today.strftime("%m")
        today_dd = today.strftime("%d")
        today_yy = today.strftime("%y")
        
        # Get the last order number
        result = await db.execute(
            select(Order.o_number).order_by(Order.o_id.desc()).limit(1)
        )
        last_number = result.scalar()
        
        if last_number and len(last_number) == 10:
            try:
                # Extract parts from last order number
                last_mm = last_number[0:2]
                last_dd = last_number[2:4]
                last_seq = int(last_number[4:8])
                last_yy = last_number[8:10]
                
                # Check if date matches today
                if last_mm == today_mm and last_dd == today_dd and last_yy == today_yy:
                    # Same day, increment sequence
                    new_seq = str(last_seq + 1).zfill(4)
                else:
                    # Different day, reset sequence
                    new_seq = "0001"
                
                return f"{today_mm}{today_dd}{new_seq}{today_yy}"
            except (ValueError, IndexError):
                # Invalid format, start fresh with today's date
                return f"{today_mm}{today_dd}0001{today_yy}"
        else:
            # No orders exist, start with 0001
            return f"{today_mm}{today_dd}0001{today_yy}"
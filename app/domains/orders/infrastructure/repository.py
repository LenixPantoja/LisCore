from typing import List, Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.domains.orders.domain.models import Order, OrdersDetail
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
        from app.domains.enterprises.domain.models import Enterprise
        result = await db.execute(
            select(Order).filter(Order.o_id == o_id).options(
                selectinload(Order.patient),
                selectinload(Order.service),
                selectinload(Order.diagnosis),
                selectinload(Order.enterprise).selectinload(Enterprise.regimen),
                selectinload(Order.enterprise).selectinload(Enterprise.classification),
                selectinload(Order.enterprise).selectinload(Enterprise.document_type),
                selectinload(Order.enterprise).selectinload(Enterprise.city),
                selectinload(Order.enterprise).selectinload(Enterprise.liability_type),
                selectinload(Order.schooling),
                selectinload(Order.tariff),
                selectinload(Order.details).selectinload(OrdersDetail.study)
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

    @staticmethod
    async def get_patient_orders_paginated(
        db: AsyncSession, 
        search_query: str,
        skip: int = 0, 
        limit: int = 100
    ) -> Tuple[Sequence[Order], int]:
        from sqlalchemy import or_
        from app.domains.patients.domain.models import Patient
        
        # Base query joining Patient
        query = select(Order).join(Patient, Order.o_his_id == Patient.pt_id).filter(
            or_(
                Patient.pt_Number_document == search_query,
                Order.o_number.ilike(f"%{search_query}%")
            )
        ).options(
            selectinload(Order.patient)
        )
        
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        result = await db.execute(query.offset(skip).limit(limit).order_by(Order.o_id.desc()))
        return result.scalars().all(), total

    @staticmethod
    async def get_order_by_number(db: AsyncSession, o_number: str) -> Optional[Order]:
        result = await db.execute(
            select(Order).filter(Order.o_number == o_number).options(
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
    async def get_laboratories_paginated(db: AsyncSession, o_id: int, skip: int = 0, limit: int = 100):
        from app.domains.laboratories.domain.models import Laboratory
        from app.domains.orders.domain.models import OrdersDetail
        
        query = select(Laboratory).join(
            OrdersDetail, OrdersDetail.od_id == Laboratory.l_order_detail_id
        ).filter(OrdersDetail.od_order_id == o_id).options(
            selectinload(Laboratory.test),
            selectinload(Laboratory.user_validation),
            selectinload(Laboratory.order_detail).selectinload(OrdersDetail.study)
        )
        
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    @staticmethod
    async def get_tests_paginated(db: AsyncSession, o_id: int, skip: int = 0, limit: int = 100):
        from app.domains.testslabs.domain.models import TestsLab
        from app.domains.studieslab.domain.models import StudiesTestDetail
        from app.domains.orders.domain.models import OrdersDetail
        
        query = select(TestsLab).join(
            StudiesTestDetail, StudiesTestDetail.tests_id == TestsLab.id
        ).join(
            OrdersDetail, OrdersDetail.od_study_id == StudiesTestDetail.studies_id
        ).filter(OrdersDetail.od_order_id == o_id).distinct()
        
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    @staticmethod
    async def get_samples_by_order_id(db: AsyncSession, o_id: int):
        from app.domains.samples.domain.models import SamplesOrder

        result = await db.execute(
            select(SamplesOrder)
            .filter(SamplesOrder.so_order_id == o_id)
            .options(selectinload(SamplesOrder.sample_type))
        )
        return result.scalars().all()
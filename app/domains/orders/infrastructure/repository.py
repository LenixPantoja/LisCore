from typing import List, Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload, contains_eager
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
        order_number: Optional[str] = None,
        patient_document: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        order_state: Optional[int] = None,
        search: Optional[str] = None
    ) -> Tuple[Sequence[Order], int]:
        from sqlalchemy import or_
        from app.domains.patients.domain.models import Patient

        # 1. Base query con relaciones
        needs_patient_join = bool(patient_document or search)
        query = select(Order).options(
            selectinload(Order.patient),
            selectinload(Order.service),
            selectinload(Order.diagnosis),
            selectinload(Order.enterprise),
            selectinload(Order.schooling),
            selectinload(Order.tariff)
        )

        if needs_patient_join:
            query = query.join(Patient, Order.o_his_id == Patient.pt_id)

        # 2. search global: número de orden o documento del paciente
        if search:
            query = query.filter(
                or_(
                    Order.o_number.ilike(f"%{search}%"),
                    Patient.pt_Number_document.ilike(f"%{search}%")
                )
            )

        # 3. Filtros específicos por campo
        if order_number:
            query = query.filter(Order.o_number.ilike(f"%{order_number}%"))

        if patient_document:
            query = query.filter(Patient.pt_Number_document.ilike(f"%{patient_document}%"))

        # 4. Filtros de rango
        if start_date:
            query = query.filter(Order.o_date >= start_date)

        if end_date:
            query = query.filter(Order.o_date <= end_date)

        if order_state is not None:
            query = query.filter(Order.o_order_state == order_state)

        # 5. Conteo total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # 6. Resultados paginados
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
    async def cancel_studies(
        db: AsyncSession,
        o_id: int,
        study_ids: list[int],
    ) -> dict:
        """
        Cancels one or more studies from an order.

        For each cancelled study:
        - Sets od_cancelled = 1 on matching OrdersDetails rows via explicit UPDATE.
        - Deletes Laboratory records linked to those OrdersDetails.
        - Sets invd_value = 0 and invd_total = 0 on matching InvoicesDetail rows.

        If ALL studies of the order end up cancelled, sets Order.o_cancelled = 1.

        Returns a dict with cancelled_detail_ids and order_cancelled flag.
        """
        from sqlalchemy import update as sa_update, delete
        from app.domains.laboratories.domain.models import Laboratory
        from app.domains.billing.domain.models import InvoiceDetail

        order = await db.get(Order, o_id)
        if not order:
            return {"cancelled_detail_ids": [], "order_cancelled": False, "not_found": True}

        # Fetch IDs of the details to cancel (only non-cancelled ones)
        to_cancel_result = await db.execute(
            select(OrdersDetail.od_id).where(
                OrdersDetail.od_order_id == o_id,
                OrdersDetail.od_study_id.in_(study_ids),
                OrdersDetail.od_cancelled == 0,
            )
        )
        cancelled_detail_ids: list[int] = list(to_cancel_result.scalars().all())

        if cancelled_detail_ids:
            # Mark as cancelled via explicit UPDATE
            await db.execute(
                sa_update(OrdersDetail)
                .where(OrdersDetail.od_id.in_(cancelled_detail_ids))
                .values(od_cancelled=1)
                .execution_options(synchronize_session="fetch")
            )

            # Delete Laboratory records linked to cancelled OrdersDetails
            await db.execute(
                delete(Laboratory).where(
                    Laboratory.l_order_detail_id.in_(cancelled_detail_ids)
                )
            )

            # Zero-out InvoiceDetail values for cancelled studies
            await db.execute(
                sa_update(InvoiceDetail)
                .where(InvoiceDetail.invd_order_detail_id.in_(cancelled_detail_ids))
                .values(invd_value=0, invd_total=0)
                .execution_options(synchronize_session="fetch")
            )

        # Check if ALL details of the order are now cancelled
        remaining_result = await db.execute(
            select(func.count()).select_from(
                select(OrdersDetail.od_id)
                .where(
                    OrdersDetail.od_order_id == o_id,
                    OrdersDetail.od_cancelled == 0,
                )
                .subquery()
            )
        )
        remaining_active = remaining_result.scalar() or 0
        all_cancelled = remaining_active == 0

        await db.execute(
            sa_update(Order)
            .where(Order.o_id == o_id)
            .values(o_cancelled=1 if all_cancelled else 0)
            .execution_options(synchronize_session="fetch")
        )

        await db.commit()

        return {
            "cancelled_detail_ids": cancelled_detail_ids,
            "order_cancelled": all_cancelled,
            "not_found": False,
        }

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
                joinedload(Order.patient),
                joinedload(Order.service),
                joinedload(Order.diagnosis),
                joinedload(Order.enterprise),
                joinedload(Order.schooling),
                joinedload(Order.tariff),
            )
        )
        return result.unique().scalars().first()

    @staticmethod
    async def get_laboratories_paginated(db: AsyncSession, o_id: int, skip: int = 0, limit: int = 100):
        from app.domains.laboratories.domain.models import Laboratory
        from app.domains.orders.domain.models import OrdersDetail
        from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail

        # Simplified count — no subquery wrapper needed
        count_stmt = (
            select(func.count())
            .select_from(Laboratory)
            .join(OrdersDetail, OrdersDetail.od_id == Laboratory.l_order_detail_id)
            .where(OrdersDetail.od_order_id == o_id)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        # JOIN StudiesLab and StudiesTestDetail to apply ordering by order_of_print / order_print.
        # contains_eager reuses the explicit JOINs instead of issuing separate SELECTs.
        result = await db.execute(
            select(Laboratory)
            .join(OrdersDetail, OrdersDetail.od_id == Laboratory.l_order_detail_id)
            .join(StudiesLab, StudiesLab.id == OrdersDetail.od_study_id)
            .outerjoin(
                StudiesTestDetail,
                (StudiesTestDetail.studies_id == OrdersDetail.od_study_id)
                & (StudiesTestDetail.tests_id == Laboratory.l_test_id),
            )
            .where(OrdersDetail.od_order_id == o_id)
            .options(
                joinedload(Laboratory.test),
                joinedload(Laboratory.user_validation),
                contains_eager(Laboratory.order_detail).contains_eager(OrdersDetail.study),
            )
            .order_by(
                StudiesLab.order_of_print.nulls_last(),
                StudiesTestDetail.order_print.nulls_last(),
                Laboratory.l_id,
            )
            .offset(skip)
            .limit(limit)
        )
        return result.unique().scalars().all(), total

    @staticmethod
    async def get_tests_paginated(db: AsyncSession, o_id: int, skip: int = 0, limit: int = 100):
        from app.domains.testslabs.domain.models import TestsLab
        from app.domains.studieslab.domain.models import StudiesTestDetail
        from app.domains.orders.domain.models import OrdersDetail

        # Direct count with COUNT(DISTINCT) — avoids wrapping a DISTINCT subquery
        count_stmt = (
            select(func.count(func.distinct(TestsLab.id)))
            .select_from(TestsLab)
            .join(StudiesTestDetail, StudiesTestDetail.tests_id == TestsLab.id)
            .join(OrdersDetail, OrdersDetail.od_study_id == StudiesTestDetail.studies_id)
            .where(OrdersDetail.od_order_id == o_id)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        # GROUP BY primary key (PostgreSQL allows this) lets us aggregate order_print
        # and sort without DISTINCT conflicts.
        result = await db.execute(
            select(TestsLab)
            .join(StudiesTestDetail, StudiesTestDetail.tests_id == TestsLab.id)
            .join(OrdersDetail, OrdersDetail.od_study_id == StudiesTestDetail.studies_id)
            .where(OrdersDetail.od_order_id == o_id)
            .group_by(TestsLab.id)
            .order_by(func.min(StudiesTestDetail.order_print).nulls_last(), TestsLab.id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_samples_by_order_id(db: AsyncSession, o_id: int):
        from app.domains.samples.domain.models import SamplesOrder

        result = await db.execute(
            select(SamplesOrder)
            .filter(SamplesOrder.so_order_id == o_id)
            .options(joinedload(SamplesOrder.sample_type))
        )
        return result.unique().scalars().all()

    @staticmethod
    async def get_study_ids_for_tariff(db: AsyncSession, tariff_id: int) -> set[int]:
        """Retorna el conjunto de study IDs que pertenecen a una tarifa."""
        from app.domains.contractstariffs.domain.models import TariffDetail
        result = await db.execute(
            select(TariffDetail.td_studie_id).where(TariffDetail.td_tariff_id == tariff_id)
        )
        return {row[0] for row in result.fetchall()}

    @staticmethod
    async def get_existing_study_ids_for_order(db: AsyncSession, o_id: int) -> set[int]:
        """Retorna el conjunto de study IDs ya registrados en una orden."""
        result = await db.execute(
            select(OrdersDetail.od_study_id).where(OrdersDetail.od_order_id == o_id)
        )
        return {row[0] for row in result.fetchall()}
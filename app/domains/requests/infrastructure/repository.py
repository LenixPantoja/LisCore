from typing import Optional
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, func, exists, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.requests.domain.models import InboundOrder, InboundOrderDetail
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail
from app.domains.testslabs.domain.models import TestsLab
from app.domains.samples.domain.models import SampleType
from app.domains.patients.domain.models import Patient


def _base_query_with_relations():
    return (
        select(InboundOrder)
        .options(
            selectinload(InboundOrder.patient).selectinload(Patient.sex_type),
            selectinload(InboundOrder.tariff),
            selectinload(InboundOrder.service),
            selectinload(InboundOrder.diagnosis),
            selectinload(InboundOrder.headquarter),
            selectinload(InboundOrder.enterprise),
            selectinload(InboundOrder.scholarity),
            selectinload(InboundOrder.details)
            .selectinload(InboundOrderDetail.study)
            .selectinload(StudiesLab.test_details)
            .selectinload(StudiesTestDetail.test)
            .selectinload(TestsLab.sample_type),
        )
    )


class InboundOrderRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict, details: list[dict]) -> InboundOrder:
        now = datetime.utcnow()
        order = InboundOrder(**data, io_created_at=now, io_updated_at=now)
        db.add(order)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Error de integridad al crear la solicitud: {exc.orig}",
            )

        for detail_data in details:
            detail = InboundOrderDetail(
                **detail_data,
                iod_inboundOrder_id=order.io_id,
                iod_created_at=now,
                iod_updated_at=now,
            )
            db.add(detail)

        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Error de integridad al guardar los detalles: {exc.orig}",
            )

        return await InboundOrderRepository.get_by_id(db, order.io_id)

    @staticmethod
    async def get_by_id(db: AsyncSession, io_id: int) -> Optional[InboundOrder]:
        result = await db.execute(
            _base_query_with_relations().filter(InboundOrder.io_id == io_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        detail_states: Optional[list[int]] = None,
        enterprise_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> tuple[int, list[InboundOrder]]:
        base = _base_query_with_relations().join(
            Patient, InboundOrder.io_patient_id == Patient.pt_id, isouter=True
        )

        if enterprise_id is not None:
            base = base.filter(InboundOrder.io_enterprise_id == enterprise_id)

        if date_from is not None:
            base = base.filter(InboundOrder.io_date_request >= date_from)

        if date_to is not None:
            base = base.filter(InboundOrder.io_date_request <= date_to)

        if search:
            pattern = f"%{search}%"
            base = base.filter(
                or_(
                    Patient.pt_Number_document.ilike(pattern),
                    InboundOrder.io_income.ilike(pattern),
                )
            )

        if detail_states:
            base = base.filter(
                exists(
                    select(InboundOrderDetail.iod_id).where(
                        InboundOrderDetail.iod_inboundOrder_id == InboundOrder.io_id,
                        InboundOrderDetail.iod_state.in_(detail_states),
                    )
                )
            )

        count_query = select(func.count()).select_from(base.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        result = await db.execute(
            base.order_by(InboundOrder.io_id.desc()).offset(skip).limit(limit)
        )
        items = result.scalars().unique().all()
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
        return await InboundOrderRepository.get_by_id(db, io_id)

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
            select(InboundOrderDetail)
            .filter(InboundOrderDetail.iod_id == iod_id)
            .options(selectinload(InboundOrderDetail.study))
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
        return await InboundOrderDetailRepository.get_by_id(db, iod_id)

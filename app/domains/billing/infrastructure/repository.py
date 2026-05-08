from typing import Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.domains.billing.domain.models import Invoice, InvoiceDetail


class InvoiceRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict, details: list[dict]) -> Invoice:
        invoice = Invoice(**data)
        db.add(invoice)
        await db.flush()

        for detail_data in details:
            detail = InvoiceDetail(invd_invoice_id=invoice.inv_id, **detail_data)
            db.add(detail)

        await db.flush()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> Tuple[Sequence[Invoice], int]:
        query = select(Invoice).options(
            selectinload(Invoice.enterprise),
            selectinload(Invoice.patient),
            selectinload(Invoice.contract),
            selectinload(Invoice.details),
        )

        if search:
            query = query.filter(Invoice.inv_number.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Invoice.inv_id.desc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, inv_id: int) -> Optional[Invoice]:
        result = await db.execute(
            select(Invoice)
            .filter(Invoice.inv_id == inv_id)
            .options(
                selectinload(Invoice.enterprise),
                selectinload(Invoice.patient),
                selectinload(Invoice.contract),
                selectinload(Invoice.details).selectinload(InvoiceDetail.study),
                selectinload(Invoice.details).selectinload(InvoiceDetail.order_detail),
            )
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, inv_id: int, update_data: dict) -> Optional[Invoice]:
        invoice = await db.get(Invoice, inv_id)
        if invoice:
            for key, value in update_data.items():
                setattr(invoice, key, value)
            await db.commit()
            await db.refresh(invoice)
        return invoice

    @staticmethod
    async def delete(db: AsyncSession, inv_id: int) -> bool:
        invoice = await db.get(Invoice, inv_id)
        if not invoice:
            return False
        await db.delete(invoice)
        await db.commit()
        return True

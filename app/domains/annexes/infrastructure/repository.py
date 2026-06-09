from typing import List, Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domains.annexes.domain.models import AnnexedResult


class AnnexedResultRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> AnnexedResult:
        ann = AnnexedResult(**data)
        db.add(ann)
        await db.flush()
        await db.refresh(ann)
        return ann

    @staticmethod
    async def get_by_id(db: AsyncSession, ar_id: int) -> Optional[AnnexedResult]:
        return await db.get(AnnexedResult, ar_id)

    @staticmethod
    async def get_by_order_id(db: AsyncSession, order_id: int) -> Sequence[AnnexedResult]:
        result = await db.execute(
            select(AnnexedResult)
            .where(AnnexedResult.ar_order_id == order_id)
            .order_by(AnnexedResult.ar_created_at.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def delete(db: AsyncSession, ar_id: int) -> Optional[AnnexedResult]:
        ann = await db.get(AnnexedResult, ar_id)
        if ann:
            await db.delete(ann)
            await db.commit()
        return ann
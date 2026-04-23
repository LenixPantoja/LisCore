from typing import List, Optional, Sequence, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.domains.testslabs.domain.models import RangeReference


class RangesReferenceRepository:
    @staticmethod
    async def create(db: AsyncSession, data: dict) -> RangeReference:
        instance = RangeReference(**data)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        return instance

    @staticmethod
    async def get_all_by_test(
        db: AsyncSession, test_id: int
    ) -> Tuple[Sequence[RangeReference], int]:
        query = select(RangeReference).where(RangeReference.test_id == test_id)
        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
        result = await db.execute(query.order_by(RangeReference.priority.asc()))
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, range_id: int) -> Optional[RangeReference]:
        result = await db.execute(
            select(RangeReference).where(RangeReference.id == range_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, range_id: int, data: dict) -> Optional[RangeReference]:
        instance = await RangesReferenceRepository.get_by_id(db, range_id)
        if not instance:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        await db.commit()
        await db.refresh(instance)
        return instance

    @staticmethod
    async def delete(db: AsyncSession, range_id: int) -> bool:
        instance = await RangesReferenceRepository.get_by_id(db, range_id)
        if not instance:
            return False
        await db.delete(instance)
        await db.commit()
        return True

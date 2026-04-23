from typing import List, Optional, Sequence, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.domains.testslabs.domain.models import ReferenceValue


class ReferenceValueRepository:
    @staticmethod
    async def create(db: AsyncSession, data: dict) -> ReferenceValue:
        instance = ReferenceValue(**data)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        return instance

    @staticmethod
    async def get_all_by_range(
        db: AsyncSession, ranges_references_id: int
    ) -> Tuple[Sequence[ReferenceValue], int]:
        query = select(ReferenceValue).where(ReferenceValue.ranges_references_id == ranges_references_id)
        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
        result = await db.execute(query.order_by(ReferenceValue.id.asc()))
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, value_id: int) -> Optional[ReferenceValue]:
        result = await db.execute(
            select(ReferenceValue).where(ReferenceValue.id == value_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, value_id: int, data: dict) -> Optional[ReferenceValue]:
        instance = await ReferenceValueRepository.get_by_id(db, value_id)
        if not instance:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        await db.commit()
        await db.refresh(instance)
        return instance

    @staticmethod
    async def delete(db: AsyncSession, value_id: int) -> bool:
        instance = await ReferenceValueRepository.get_by_id(db, value_id)
        if not instance:
            return False
        await db.delete(instance)
        await db.commit()
        return True

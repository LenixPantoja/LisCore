from typing import List, Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.domains.Headquarters.domain.models import Headquarter

class HeadquarterRepository:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Headquarter]:
        result = await db.execute(select(Headquarter))
        return result.scalars().all()

    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[Headquarter], int]:
        """Get headquarters with pagination"""
        query = select(Headquarter)

        if search:
            query = query.filter(Headquarter.name.ilike(f"%{search}%"))
        if active is not None:
            query = query.filter(Headquarter.active == active)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Headquarter.id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, headquarter_id: int) -> Optional[Headquarter]:
        result = await db.execute(select(Headquarter).filter(Headquarter.id == headquarter_id))
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, headquarter_data: dict) -> Headquarter:
        new_hq = Headquarter(**headquarter_data)
        db.add(new_hq)
        await db.commit()
        await db.refresh(new_hq)
        return new_hq

    @staticmethod
    async def update(db: AsyncSession, headquarter_id: int, update_data: dict) -> Optional[Headquarter]:
        result = await db.execute(select(Headquarter).filter(Headquarter.id == headquarter_id))
        hq = result.scalars().first()
        if hq:
            for key, value in update_data.items():
                setattr(hq, key, value)
            await db.commit()
            await db.refresh(hq)
        return hq

    @staticmethod
    async def delete(db: AsyncSession, headquarter_id: int) -> bool:
        result = await db.execute(select(Headquarter).filter(Headquarter.id == headquarter_id))
        hq = result.scalars().first()
        if hq:
            await db.delete(hq)
            await db.commit()
            return True
        return False
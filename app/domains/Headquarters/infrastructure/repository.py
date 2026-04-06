from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.domains.Headquarters.domain.models import Headquarter

class HeadquarterRepository:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Headquarter]:
        result = await db.execute(select(Headquarter))
        return result.scalars().all()

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
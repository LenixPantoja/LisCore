from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.domains.samples.domain.models import SampleType

class SampleRepository:
    @staticmethod
    async def get_all_types(db: AsyncSession) -> List[SampleType]:
        result = await db.execute(select(SampleType))
        return result.scalars().all()

    @staticmethod
    async def get_type_by_id(db: AsyncSession, st_id: int) -> Optional[SampleType]:
        return await db.get(SampleType, st_id)

    @staticmethod
    async def create_type(db: AsyncSession, data: dict) -> SampleType:
        new_type = SampleType(**data)
        db.add(new_type)
        await db.commit()
        await db.refresh(new_type)
        return new_type

    @staticmethod
    async def update_type(db: AsyncSession, st_id: int, data: dict) -> Optional[SampleType]:
        item = await db.get(SampleType, st_id)
        if item:
            for key, value in data.items():
                setattr(item, key, value)
            await db.commit()
            await db.refresh(item)
        return item

    @staticmethod
    async def delete_type(db: AsyncSession, st_id: int) -> bool:
        item = await db.get(SampleType, st_id)
        if item:
            await db.delete(item)
            await db.commit()
            return True
        return False
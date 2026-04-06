from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.domains.testslabs.domain.models import TestsLab

class TestsLabRepository:
    @staticmethod
    async def create(db: AsyncSession, data: dict) -> TestsLab:
        new_test = TestsLab(**data)
        db.add(new_test)
        await db.commit()
        await db.refresh(new_test)
        return new_test

    @staticmethod
    async def get_all(db: AsyncSession) -> List[TestsLab]:
        result = await db.execute(
            select(TestsLab).options(
                selectinload(TestsLab.technique),
                selectinload(TestsLab.work_group),
                selectinload(TestsLab.sample_type)
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, test_id: int) -> Optional[TestsLab]:
        result = await db.execute(
            select(TestsLab).filter(TestsLab.id == test_id).options(
                selectinload(TestsLab.technique),
                selectinload(TestsLab.work_group),
                selectinload(TestsLab.sample_type)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, test_id: int, update_data: dict) -> Optional[TestsLab]:
        test = await db.get(TestsLab, test_id)
        if test:
            for key, value in update_data.items():
                setattr(test, key, value)
            await db.commit()
            await db.refresh(test)
        return test

    @staticmethod
    async def delete(db: AsyncSession, test_id: int) -> bool:
        test = await db.get(TestsLab, test_id)
        if test:
            await db.delete(test)
            await db.commit()
            return True
        return False
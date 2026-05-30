from typing import List, Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.domains.testslabs.domain.models import TestslabFormatComplete


class TestslabFormatCompleteRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> TestslabFormatComplete:
        record = TestslabFormatComplete(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        # Reload with related format_complete
        return await TestslabFormatCompleteRepository.get_by_id(db, record.tfc_id)

    @staticmethod
    async def get_by_testslab(
        db: AsyncSession, testslab_id: int
    ) -> Sequence[TestslabFormatComplete]:
        result = await db.execute(
            select(TestslabFormatComplete)
            .where(TestslabFormatComplete.tfc_testslab_id == testslab_id)
            .options(selectinload(TestslabFormatComplete.format_complete))
            .order_by(TestslabFormatComplete.tfc_order_index.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(
        db: AsyncSession, tfc_id: int
    ) -> Optional[TestslabFormatComplete]:
        result = await db.execute(
            select(TestslabFormatComplete)
            .where(TestslabFormatComplete.tfc_id == tfc_id)
            .options(selectinload(TestslabFormatComplete.format_complete))
        )
        return result.scalars().first()

    @staticmethod
    async def exists(
        db: AsyncSession, testslab_id: int, format_complete_id: int
    ) -> bool:
        result = await db.execute(
            select(TestslabFormatComplete.tfc_id).where(
                TestslabFormatComplete.tfc_testslab_id == testslab_id,
                TestslabFormatComplete.tfc_format_complete_id == format_complete_id,
            )
        )
        return result.scalar() is not None

    @staticmethod
    async def update(
        db: AsyncSession, tfc_id: int, data: dict
    ) -> Optional[TestslabFormatComplete]:
        record = await db.get(TestslabFormatComplete, tfc_id)
        if record:
            for key, value in data.items():
                setattr(record, key, value)
            await db.commit()
            return await TestslabFormatCompleteRepository.get_by_id(db, tfc_id)
        return None

    @staticmethod
    async def delete(db: AsyncSession, tfc_id: int) -> bool:
        record = await db.get(TestslabFormatComplete, tfc_id)
        if record:
            await db.delete(record)
            await db.commit()
            return True
        return False

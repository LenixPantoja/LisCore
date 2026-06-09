from typing import List, Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.domains.testslabs.domain.models import FormatComplete


class FormatCompleteRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> FormatComplete:
        record = FormatComplete(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> Tuple[Sequence[FormatComplete], int]:
        query = select(FormatComplete)
        if search:
            query = query.where(FormatComplete.fc_name.ilike(f"%{search}%"))
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        result = await db.execute(
            query.offset(skip).limit(limit).order_by(FormatComplete.fc_name.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, fc_id: int) -> Optional[FormatComplete]:
        result = await db.execute(
            select(FormatComplete).where(FormatComplete.fc_id == fc_id)
        )
        return result.scalars().first()

    @staticmethod
    async def update(
        db: AsyncSession, fc_id: int, data: dict
    ) -> Optional[FormatComplete]:
        record = await db.get(FormatComplete, fc_id)
        if record:
            for key, value in data.items():
                setattr(record, key, value)
            await db.commit()
            await db.refresh(record)
        return record

    @staticmethod
    async def delete(db: AsyncSession, fc_id: int) -> bool:
        record = await db.get(FormatComplete, fc_id)
        if record:
            await db.delete(record)
            await db.commit()
            return True
        return False

from typing import Tuple, Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String
from app.domains.samples.domain.models import SampleType

class SampleRepository:
    @staticmethod
    async def get_types_paginated(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None
    ) -> Tuple[Sequence[SampleType], int]:
        query = select(SampleType)
        
        if search:
            query = query.filter(
                (SampleType.st_name.ilike(f"%{search}%"))
                | (cast(SampleType.st_sufix, String).ilike(f"%{search}%"))
            )
        
        # Conteo total para paginación
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        # Resultados paginados ordenados por nombre
        result = await db.execute(
            query.offset(skip).limit(limit).order_by(SampleType.st_name.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_type_by_id(db: AsyncSession, st_id: int) -> Optional[SampleType]:
        return await db.get(SampleType, st_id)

    @staticmethod
    async def create_type(db: AsyncSession, data: dict) -> SampleType:
        new_item = SampleType(**data)
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        return new_item

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

    @staticmethod
    async def get_all_types(db: AsyncSession) -> Sequence[SampleType]:
        result = await db.execute(
            select(SampleType).order_by(SampleType.st_name.asc())
        )
        return result.scalars().all()
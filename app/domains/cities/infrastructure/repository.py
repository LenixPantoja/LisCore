from typing import Tuple, Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.domains.masters.domain.models import City

class CityRepository:
    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        department_id: Optional[int] = None
    ) -> Tuple[Sequence[City], int]:
        """Get cities with pagination"""
        query = select(City)

        if department_id is not None:
            query = query.filter(City.Department_id == department_id)
        if search:
            query = query.filter(
                City.city_name.ilike(f"%{search}%") | City.city_code.ilike(f"%{search}%")
            )

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(City.id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, city_id: int):
        """Get city by ID"""
        return await db.get(City, city_id)

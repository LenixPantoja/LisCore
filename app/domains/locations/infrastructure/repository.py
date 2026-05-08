from typing import Tuple, Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.domains.locations.domain.models import Location

class LocationRepository:
    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[Location], int]:
        """Get locations with pagination"""
        query = select(Location)

        if search:
            query = query.filter(Location.loc_name.ilike(f"%{search}%"))
        if active is not None:
            query = query.filter(Location.loc_active == active)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Location.loc_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, loc_id: int) -> Optional[Location]:
        """Get location by ID"""
        return await db.get(Location, loc_id)

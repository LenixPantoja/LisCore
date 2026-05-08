from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.samples.infrastructure.repository import SampleRepository

async def execute(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None):
    items, total = await SampleRepository.get_types_paginated(db, skip, limit, search)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import UserRepository

async def execute(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None):
    items, total = await UserRepository.get_paginated(db, skip, limit, search)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }
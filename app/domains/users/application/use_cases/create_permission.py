from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import PermissionRepository


async def execute(db: AsyncSession, data: dict):
    existing = await PermissionRepository.get_by_name(db, data["p_name"])
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Permission '{data['p_name']}' already exists",
        )
    return await PermissionRepository.create(db, data)

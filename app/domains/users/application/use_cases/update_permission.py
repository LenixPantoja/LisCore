from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import PermissionRepository


async def execute(db: AsyncSession, permission_id: int, data: dict):
    permission = await PermissionRepository.get_by_id(db, permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    if "p_name" in data and data["p_name"] != permission.p_name:
        existing = await PermissionRepository.get_by_name(db, data["p_name"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Permission '{data['p_name']}' already exists",
            )

    return await PermissionRepository.update(db, permission, data)

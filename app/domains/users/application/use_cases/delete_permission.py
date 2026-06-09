from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import PermissionRepository


async def execute(db: AsyncSession, permission_id: int) -> None:
    permission = await PermissionRepository.get_by_id(db, permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    await PermissionRepository.delete(db, permission)

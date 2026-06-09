from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import PermissionRepository


async def execute(db: AsyncSession, rol_id: int) -> list:
    return await PermissionRepository.get_permissions_by_role(db, rol_id)


async def assign(db: AsyncSession, rol_id: int, permission_id: int) -> None:
    permission = await PermissionRepository.get_by_id(db, permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    await PermissionRepository.assign_permission_to_role(db, rol_id, permission_id)


async def remove(db: AsyncSession, rol_id: int, permission_id: int) -> None:
    await PermissionRepository.remove_permission_from_role(db, rol_id, permission_id)


async def toggle_active(db: AsyncSession, rol_id: int, permission_id: int, active: bool) -> None:
    updated = await PermissionRepository.toggle_permission_active(db, rol_id, permission_id, active)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role-permission association not found",
        )

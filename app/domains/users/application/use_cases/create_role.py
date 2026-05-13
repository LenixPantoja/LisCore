from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import RolRepository, PermissionRepository


async def execute(db: AsyncSession, data: dict):
    permission_ids = data.pop("permission_ids", None) or []

    existing = await RolRepository.get_by_name(db, data["r_name"])
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un rol con el nombre '{data['r_name']}'",
        )

    rol = await RolRepository.create(db, data)

    for pid in permission_ids:
        await PermissionRepository.assign_permission_to_role(db, rol.r_id, pid)

    return await RolRepository.get_by_id_with_permissions(db, rol.r_id)


from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import RolRepository, PermissionRepository


async def execute(db: AsyncSession, rol_id: int, data: dict):
    permission_ids = data.pop("permission_ids", None)

    rol = await RolRepository.get_by_id(db, rol_id)
    if not rol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    # Verificar nombre duplicado si se está cambiando
    new_name = data.get("r_name")
    if new_name and new_name != rol.r_name:
        existing = await RolRepository.get_by_name(db, new_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un rol con el nombre '{new_name}'",
            )

    # Actualizar campos del rol (solo los enviados)
    if data:
        await RolRepository.update(db, rol, data)

    # Reemplazar permisos si se envió permission_ids (lista vacía = quitar todos)
    if permission_ids is not None:
        await PermissionRepository.clear_permissions_from_role(db, rol_id)
        for pid in permission_ids:
            await PermissionRepository.assign_permission_to_role(db, rol_id, pid)

    return await RolRepository.get_by_id_with_permissions(db, rol_id)

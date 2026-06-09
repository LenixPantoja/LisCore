from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import RolRepository


async def execute(db: AsyncSession, rol_id: int):
    rol = await RolRepository.get_by_id_with_permissions(db, rol_id)
    if not rol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    return rol

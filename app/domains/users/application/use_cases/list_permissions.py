from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import PermissionRepository


async def execute(db: AsyncSession) -> list:
    return await PermissionRepository.get_all(db)

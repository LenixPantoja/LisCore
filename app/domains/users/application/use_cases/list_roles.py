from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import RolRepository


async def execute(db: AsyncSession) -> list:
    return await RolRepository.get_all(db)

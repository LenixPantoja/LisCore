from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.masters.infrastructure.repository import MastersRepository

async def execute(db: AsyncSession):
    """
    Retrieves all services from the repository.
    """
    return await MastersRepository.get_all_services(db)
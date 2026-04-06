from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.masters.infrastructure.repository import MastersRepository
from app.domains.masters.domain.models import Country

async def execute(db: AsyncSession) -> List[Country]:
    """
    Retrieves all active countries from the repository.
    """
    return await MastersRepository.get_all_countries(db)
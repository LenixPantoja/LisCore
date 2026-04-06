from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.masters.infrastructure.repository import MastersRepository
from app.domains.masters.domain.models import Department

async def execute(db: AsyncSession, country_id: int) -> List[Department]:
    """
    Retrieves all departments associated with a given country ID.
    """
    return await MastersRepository.get_departments_by_country_id(db, country_id)
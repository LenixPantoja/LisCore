from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.masters.infrastructure.repository import MastersRepository
from app.domains.masters.domain.models import City

async def execute(db: AsyncSession, department_id: int) -> List[City]:
    """
    Retrieves all cities associated with a given department ID.
    """
    return await MastersRepository.get_cities_by_department_id(db, department_id)
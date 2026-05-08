from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.masters.infrastructure.repository import MastersRepository

async def execute(db: AsyncSession):
    return await MastersRepository.get_all_sex_types(db)
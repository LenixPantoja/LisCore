from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.enterprises.infrastructure.repository import EnterpriseRepository
from fastapi import HTTPException, status

async def execute(db: AsyncSession, enterprise_id: int):
    enterprise = await EnterpriseRepository.get_by_id(db, enterprise_id)
    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enterprise not found"
        )
    return enterprise
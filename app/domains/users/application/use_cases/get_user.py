from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import UserRepository
from fastapi import HTTPException, status

async def execute(db: AsyncSession, user_id: int):
    user = await UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.domain.interfaces import UserRepository
from fastapi import HTTPException, status
from app.domains.users.domain.models import User

async def execute(user_repo: UserRepository, db: AsyncSession, user_data: dict) -> User:
    # Check if user already exists
    existing_user = await user_repo.get_by_login(db, user_data["usr_login"])
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # The password hashing is handled internally by the repository implementation
    return await user_repo.create(db, user_data)

from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import UserRepository
from fastapi import HTTPException, status

async def execute(db: AsyncSession, user_data: dict):
    # Check if user already exists
    existing_user = await UserRepository.get_by_login(db, user_data["usr_login"])
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # El hasheo de la contraseña se maneja internamente en UserRepository.create
    return await UserRepository.create(db, user_data)

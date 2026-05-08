from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import UserRepository
from fastapi import HTTPException, status
from app.domains.users.infrastructure.models import AppUser

async def execute(user_repo: UserRepository, db: AsyncSession, user_id: int, update_data: dict) -> AppUser:
    user = await user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Si se intenta cambiar el login, verificamos que el nuevo no esté registrado
    if "usr_login" in update_data and update_data["usr_login"] != user.usr_login:
        existing_user = await user_repo.get_by_login(db, update_data["usr_login"])
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nuevo nombre de usuario ya está en uso"
            )

    return await user_repo.update(db, user, update_data)

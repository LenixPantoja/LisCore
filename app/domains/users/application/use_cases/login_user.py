from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import UserRepository
from fastapi import HTTPException, status
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from datetime import timedelta

async def execute(user_repo: UserRepository, db: AsyncSession, login_data: dict):
    user = await user_repo.get_by_login(db, login_data["usr_login"])
    
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
        
    if not verify_password(login_data["usr_password"], user.usr_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    if user.usr_is_Locked or not user.usr_is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is locked or inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.usr_login, "id": user.usr_id},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "username": user.usr_login,
    }

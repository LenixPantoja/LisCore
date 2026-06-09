from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token
from app.domains.users.infrastructure.repository import UserRepository
from datetime import timedelta


async def execute(db: AsyncSession, refresh_token: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "refresh":
        raise credentials_exception

    user_id: int = payload.get("id")
    if user_id is None:
        raise credentials_exception

    user = await UserRepository.get_by_id(db, user_id)
    if user is None or not user.usr_is_active or user.usr_is_Locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is locked or inactive",
        )

    access_token = create_access_token(
        data={"sub": user.usr_login, "id": user.usr_id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {"access_token": access_token, "token_type": "bearer"}

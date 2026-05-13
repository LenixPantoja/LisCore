from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.domains.users.infrastructure.models import AppUser
from app.domains.users.infrastructure.repository import PermissionRepository

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> AppUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(
        select(AppUser)
        .filter(AppUser.usr_id == user_id)
        .options(selectinload(AppUser.role))
    )
    user = result.scalars().first()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.usr_is_active or user.usr_is_Locked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive or locked")

    return user


def require_permission(permission_name: str):
    """
    Dependency factory that verifies the current user's role has the given permission.

    Usage:
        @router.get("/resource", dependencies=[Depends(require_permission("view_resource"))])
    """
    async def _check(
        current_user: AppUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> AppUser:
        has_permission = await PermissionRepository.role_has_permission(
            db, current_user.usr_rol_id, permission_name
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' required",
            )
        return current_user

    return _check

import time
from typing import Dict, Tuple, Optional

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

# ---------------------------------------------------------------------------
# In-memory TTL cache for permission checks.
# Key: (rol_id, permission_name) → (result: bool, timestamp: float)
# This avoids a DB JOIN on every authenticated request.
# ---------------------------------------------------------------------------
_permission_cache: Dict[Tuple[int, str], Tuple[bool, float]] = {}
_PERMISSION_CACHE_TTL: float = 60.0  # seconds


def _get_cached_permission(rol_id: int, permission_name: str) -> Optional[bool]:
    entry = _permission_cache.get((rol_id, permission_name))
    if entry is not None:
        value, ts = entry
        if time.monotonic() - ts < _PERMISSION_CACHE_TTL:
            return value
        del _permission_cache[(rol_id, permission_name)]
    return None


def _set_cached_permission(rol_id: int, permission_name: str, value: bool) -> None:
    _permission_cache[(rol_id, permission_name)] = (value, time.monotonic())


def invalidate_permission_cache(rol_id: Optional[int] = None) -> None:
    """Call this whenever role permissions are modified."""
    if rol_id is None:
        _permission_cache.clear()
    else:
        keys = [k for k in _permission_cache if k[0] == rol_id]
        for k in keys:
            del _permission_cache[k]


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
    Permission results are cached in-memory for up to 60 seconds per role.

    Usage:
        @router.get("/resource", dependencies=[Depends(require_permission("view_resource"))])
    """
    async def _check(
        current_user: AppUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> AppUser:
        cached = _get_cached_permission(current_user.usr_rol_id, permission_name)
        if cached is None:
            cached = await PermissionRepository.role_has_permission(
                db, current_user.usr_rol_id, permission_name
            )
            _set_cached_permission(current_user.usr_rol_id, permission_name, cached)
        if not cached:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' required",
            )
        return current_user

    return _check

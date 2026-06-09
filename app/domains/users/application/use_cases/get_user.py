from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.domains.users.infrastructure.repository import UserRepository, PermissionRepository
from app.domains.users.infrastructure.models import AppUser
from fastapi import HTTPException, status
from utils.minio_client import get_signature_url


async def execute(db: AsyncSession, user_id: int) -> dict:
    result = await db.execute(
        select(AppUser)
        .filter(AppUser.usr_id == user_id)
        .options(selectinload(AppUser.role))
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    permissions = await PermissionRepository.get_permissions_by_role(db, user.usr_rol_id)

    return {
        **{c.name: getattr(user, c.name) for c in user.__table__.columns},
        "role": user.role,
        "permissions": permissions,
        "signature_url": get_signature_url(user.usr_Signature),
    }
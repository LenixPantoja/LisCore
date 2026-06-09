from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.domains.users.infrastructure.repository import UserRepository, PermissionRepository
from app.domains.users.infrastructure.models import AppUser
from app.core.security import get_password_hash
from fastapi import HTTPException, status
from utils.minio_client import upload_signature, build_signature_object_name


async def execute(
    user_repo: UserRepository,
    db: AsyncSession,
    user_data: dict,
    permission_ids: Optional[List[int]] = None,
    signature_bytes: Optional[bytes] = None,
    signature_extension: str = "png",
) -> AppUser:
    existing_user = await user_repo.get_by_login(db, user_data["usr_login"])
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    user_data = dict(user_data)
    user_data["usr_password"] = get_password_hash(user_data["usr_password"])

    new_user = await user_repo.create(db, user_data)

    if permission_ids:
        for pid in permission_ids:
            await PermissionRepository.assign_permission_to_role(db, new_user.usr_rol_id, pid)

    if signature_bytes:
        object_name = build_signature_object_name(new_user.usr_id, signature_extension)
        upload_signature(signature_bytes, object_name)
        new_user.usr_Signature = object_name
        await db.commit()
        await db.refresh(new_user)

    result = await db.execute(
        select(AppUser)
        .filter(AppUser.usr_id == new_user.usr_id)
        .options(selectinload(AppUser.role))
    )
    return result.scalars().first()

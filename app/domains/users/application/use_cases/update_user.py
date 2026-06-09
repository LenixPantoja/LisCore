from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.domains.users.infrastructure.repository import UserRepository, PermissionRepository
from app.core.security import get_password_hash
from fastapi import HTTPException, status
from app.domains.users.infrastructure.models import AppUser
from utils.minio_client import upload_signature, build_signature_object_name


async def execute(
    user_repo: UserRepository,
    db: AsyncSession,
    user_id: int,
    update_data: dict,
    signature_bytes: Optional[bytes] = None,
    signature_extension: str = "png",
) -> AppUser:
    user = await user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    permission_ids = update_data.pop("permission_ids", None)

    if "usr_login" in update_data and update_data["usr_login"] != user.usr_login:
        existing_user = await user_repo.get_by_login(db, update_data["usr_login"])
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nuevo nombre de usuario ya está en uso"
            )

    if update_data.get("usr_password"):
        update_data["usr_password"] = get_password_hash(update_data["usr_password"])

    if signature_bytes:
        object_name = build_signature_object_name(user_id, signature_extension)
        upload_signature(signature_bytes, object_name)
        update_data["usr_Signature"] = object_name

    updated_user = await user_repo.update(db, user, update_data)

    if permission_ids is not None:
        rol_id = updated_user.usr_rol_id
        await PermissionRepository.clear_permissions_from_role(db, rol_id)
        for pid in permission_ids:
            await PermissionRepository.assign_permission_to_role(db, rol_id, pid)

    result = await db.execute(
        select(AppUser)
        .filter(AppUser.usr_id == updated_user.usr_id)
        .options(selectinload(AppUser.role))
    )
    return result.scalars().first()

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.domains.users.infrastructure.models import AppUser
from app.core.security import verify_password, get_password_hash


async def execute(
    db: AsyncSession,
    current_user: AppUser,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, current_user.usr_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta.",
        )

    if verify_password(new_password, current_user.usr_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña no puede ser igual a la actual.",
        )

    current_user.usr_password = get_password_hash(new_password)
    current_user.usr_must_change_password = False
    db.add(current_user)
    await db.commit()

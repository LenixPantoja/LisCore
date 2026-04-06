from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.domains.users.infrastructure.models import AppUser, Rol
from app.domains.users.domain.models import User
from app.domains.users.domain.interfaces import UserRepository as AbstractUserRepository
from app.core.security import get_password_hash

class UserRepository(AbstractUserRepository):

    def _to_domain_model(self, app_user: AppUser) -> User:
        """Converts an ORM AppUser model to a domain User model."""
        return User(
            usr_id=app_user.usr_id,
            usr_login=app_user.usr_login,
            usr_first_name=app_user.usr_first_name,
            usr_middle_name=app_user.usr_middle_name,
            usr_last_name=app_user.usr_last_name,
            usr_second_last_name=app_user.usr_second_last_name,
            usr_document_number=app_user.usr_document_number,
            usr_phone_number=app_user.usr_phone_number,
            usr_is_active=app_user.usr_is_active,
            usr_mail=app_user.usr_mail,
            usr_rol_id=app_user.usr_rol_id,
            usr_is_Locked=app_user.usr_is_Locked,
            usr_Signature=app_user.usr_Signature,
            usr_created_at=app_user.usr_created_at,
            usr_updated_at=app_user.usr_updated_at,
            usr_password=app_user.usr_password # Include hashed password for internal use (e.g., verification)
        )

    async def get_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(AppUser).filter(AppUser.usr_id == user_id))
        app_user = result.scalars().first()
        return self._to_domain_model(app_user) if app_user else None

    async def get_by_login(self, db: AsyncSession, login: str) -> Optional[User]:
        result = await db.execute(select(AppUser).filter(AppUser.usr_login == login))
        app_user = result.scalars().first()
        return self._to_domain_model(app_user) if app_user else None

    async def create(self, db: AsyncSession, user_data: dict) -> User:
        if "usr_password" in user_data:
            user_data["usr_password"] = get_password_hash(user_data["usr_password"])
        new_user = AppUser(**user_data)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return self._to_domain_model(new_user)

    async def update(self, db: AsyncSession, user: User, update_data: dict) -> User:
        if "usr_password" in update_data:
            update_data["usr_password"] = get_password_hash(update_data["usr_password"])
        
        # Fetch the ORM object to update
        app_user_to_update = await db.get(AppUser, user.usr_id)
        for key, value in update_data.items(): # Apply updates to the ORM object
            if key == "usr_id":
                continue
            setattr(app_user_to_update, key, value)
        await db.commit()
        await db.refresh(app_user_to_update)
        return self._to_domain_model(app_user_to_update)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import AppUser
from app.core.security import get_password_hash

class UserRepository:

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int):
        result = await db.execute(select(AppUser).filter(AppUser.usr_id == user_id))
        return result.scalars().first()

    @staticmethod
    async def get_by_login(db: AsyncSession, login: str):
        result = await db.execute(select(AppUser).filter(AppUser.usr_login == login))
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, user_data: dict):
        if "usr_password" in user_data:
            user_data["usr_password"] = get_password_hash(user_data["usr_password"])
        new_user = AppUser(**user_data)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    async def update(db: AsyncSession, user: AppUser, update_data: dict):
        if "usr_password" in update_data:
            update_data["usr_password"] = get_password_hash(update_data["usr_password"])
        for key, value in update_data.items():
            setattr(user, key, value)
        await db.commit()
        await db.refresh(user)
        return user

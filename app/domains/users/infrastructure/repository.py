from typing import Tuple, Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.domains.users.infrastructure.models import AppUser

class UserRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> AppUser | None:
        """
        Retrieves a user by its ID.
        """
        return await db.get(AppUser, user_id)

    @staticmethod
    async def get_paginated(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None
    ) -> Tuple[Sequence[AppUser], int]:
        query = select(AppUser)
        if search:
            # Asumiendo que quieres buscar por nombre, apellido o login
            query = query.filter(
                (AppUser.usr_first_name.ilike(f"%{search}%")) | 
                (AppUser.usr_last_name.ilike(f"%{search}%")) |
                (AppUser.usr_login.ilike(f"%{search}%"))
            )
        
        # Contar el total de elementos antes de aplicar paginación
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        # Obtener los elementos paginados
        result = await db.execute(
            query.offset(skip)
            .limit(limit)
            .order_by(AppUser.usr_first_name.asc()) # Ordenar por nombre de usuario
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_by_login(db: AsyncSession, login: str) -> Optional[AppUser]:
        """
        Retrieves a user by its login.
        """
        result = await db.execute(select(AppUser).filter(AppUser.usr_login == login))
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, user_data: dict) -> AppUser:
        """
        Creates a new user record in the database.
        """
        new_user = AppUser(**user_data)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    async def update(db: AsyncSession, user: AppUser, update_data: dict) -> AppUser:
        """
        Updates an existing user record.
        """
        for key, value in update_data.items():
            setattr(user, key, value)
        
        await db.commit()
        await db.refresh(user)
        return user
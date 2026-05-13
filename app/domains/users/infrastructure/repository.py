from typing import Tuple, Sequence, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from app.domains.users.infrastructure.models import AppUser, Permission, RolPermission, Rol


class RolRepository:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Rol]:
        result = await db.execute(select(Rol).order_by(Rol.r_name))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Rol | None:
        result = await db.execute(select(Rol).where(Rol.r_name == name))
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> Rol:
        rol = Rol(**data)
        db.add(rol)
        await db.commit()
        await db.refresh(rol)
        return rol

    @staticmethod
    async def get_by_id_with_permissions(db: AsyncSession, rol_id: int) -> Rol | None:
        result = await db.execute(
            select(Rol).where(Rol.r_id == rol_id).options(selectinload(Rol.permissions))
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_id(db: AsyncSession, rol_id: int) -> Rol | None:
        return await db.get(Rol, rol_id)

    @staticmethod
    async def update(db: AsyncSession, rol: Rol, data: dict) -> Rol:
        for key, value in data.items():
            setattr(rol, key, value)
        await db.commit()
        await db.refresh(rol)
        return rol


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
        Retrieves a user by its login with role relationship loaded.
        """
        result = await db.execute(
            select(AppUser)
            .filter(AppUser.usr_login == login)
            .options(selectinload(AppUser.role))
        )
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


class PermissionRepository:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Permission]:
        result = await db.execute(select(Permission).order_by(Permission.p_module, Permission.p_name))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, permission_id: int) -> Optional[Permission]:
        return await db.get(Permission, permission_id)

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[Permission]:
        result = await db.execute(select(Permission).filter(Permission.p_name == name))
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> Permission:
        permission = Permission(**data)
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
        return permission

    @staticmethod
    async def update(db: AsyncSession, permission: Permission, data: dict) -> Permission:
        for key, value in data.items():
            setattr(permission, key, value)
        await db.commit()
        await db.refresh(permission)
        return permission

    @staticmethod
    async def delete(db: AsyncSession, permission: Permission) -> None:
        await db.delete(permission)
        await db.commit()

    @staticmethod
    async def get_permissions_by_role(db: AsyncSession, rol_id: int, only_active: bool = True) -> List[Permission]:
        query = (
            select(Permission)
            .join(RolPermission, Permission.p_id == RolPermission.rp_permission_id)
            .filter(RolPermission.rp_rol_id == rol_id)
        )
        if only_active:
            query = query.filter(RolPermission.rp_active == True)
        result = await db.execute(query.order_by(Permission.p_module, Permission.p_name))
        return list(result.scalars().all())

    @staticmethod
    async def assign_permission_to_role(db: AsyncSession, rol_id: int, permission_id: int) -> None:
        existing = await db.execute(
            select(RolPermission).filter(
                RolPermission.rp_rol_id == rol_id,
                RolPermission.rp_permission_id == permission_id
            )
        )
        existing_record = existing.scalars().first()
        if existing_record is None:
            db.add(RolPermission(rp_rol_id=rol_id, rp_permission_id=permission_id, rp_active=True))
            await db.commit()
        elif not existing_record.rp_active:
            existing_record.rp_active = True
            await db.commit()

    @staticmethod
    async def remove_permission_from_role(db: AsyncSession, rol_id: int, permission_id: int) -> None:
        await db.execute(
            delete(RolPermission).where(
                RolPermission.rp_rol_id == rol_id,
                RolPermission.rp_permission_id == permission_id
            )
        )
        await db.commit()

    @staticmethod
    async def clear_permissions_from_role(db: AsyncSession, rol_id: int) -> None:
        await db.execute(delete(RolPermission).where(RolPermission.rp_rol_id == rol_id))
        await db.commit()

    @staticmethod
    async def toggle_permission_active(
        db: AsyncSession, rol_id: int, permission_id: int, active: bool
    ) -> bool:
        result = await db.execute(
            select(RolPermission).filter(
                RolPermission.rp_rol_id == rol_id,
                RolPermission.rp_permission_id == permission_id,
            )
        )
        record = result.scalars().first()
        if record is None:
            return False
        record.rp_active = active
        await db.commit()
        return True

    @staticmethod
    async def role_has_permission(db: AsyncSession, rol_id: int, permission_name: str) -> bool:
        result = await db.execute(
            select(RolPermission)
            .join(Permission, Permission.p_id == RolPermission.rp_permission_id)
            .filter(
                RolPermission.rp_rol_id == rol_id,
                Permission.p_name == permission_name,
                RolPermission.rp_active == True,
            )
        )
        return result.scalars().first() is not None
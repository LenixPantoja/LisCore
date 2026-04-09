from typing import Tuple, Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.domains.enterprises.domain.models import Enterprise

class EnterpriseRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, enterprise_id: int) -> Enterprise | None:
        """
        Retrieves an enterprise by its ID.
        """
        return await db.get(Enterprise, enterprise_id)

    @staticmethod
    async def get_by_code(db: AsyncSession, enterprise_code: str) -> Enterprise | None:
        """
        Retrieves an enterprise by its code.
        """
        result = await db.execute(select(Enterprise).filter(Enterprise.en_code == enterprise_code))
        return result.scalars().first()

    @staticmethod
    async def get_by_nit(db: AsyncSession, enterprise_nit: str) -> Enterprise | None:
        """
        Retrieves an enterprise by its NIT.
        """
        result = await db.execute(select(Enterprise).filter(Enterprise.en_nit == enterprise_nit))
        return result.scalars().first()

    @staticmethod
    async def get_by_mail(db: AsyncSession, enterprise_mail: str) -> Enterprise | None:
        """
        Retrieves an enterprise by its email.
        """
        result = await db.execute(select(Enterprise).filter(Enterprise.en_mail == enterprise_mail))
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, enterprise_data: dict) -> Enterprise:
        """
        Creates a new enterprise in the database.
        """
        new_enterprise = Enterprise(**enterprise_data)
        db.add(new_enterprise)
        await db.commit()
        await db.refresh(new_enterprise)
        return new_enterprise

    @staticmethod
    async def update(db: AsyncSession, enterprise: Enterprise, update_data: dict) -> Enterprise:
        """
        Updates an existing enterprise record.
        """
        for key, value in update_data.items():
            setattr(enterprise, key, value)
        
        await db.commit()
        await db.refresh(enterprise)
        return enterprise

    @staticmethod
    async def get_paginated(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None
    ) -> Tuple[Sequence[Enterprise], int]:
        query = select(Enterprise)
        if search:
            query = query.filter(
                (Enterprise.en_name.ilike(f"%{search}%")) | 
                (Enterprise.en_nit.ilike(f"%{search}%")) |
                (Enterprise.en_code.ilike(f"%{search}%"))
            )
        
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        result = await db.execute(query.offset(skip).limit(limit).order_by(Enterprise.en_name.asc()))
        return result.scalars().all(), total
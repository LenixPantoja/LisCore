from typing import Tuple, Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.domains.enterprises.domain.models import Enterprise

class EnterpriseRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, enterprise_id: int) -> Enterprise | None:
        """
        Retrieves an enterprise by its ID, including all related entities.
        """
        result = await db.execute(
            select(Enterprise)
            .options(
                selectinload(Enterprise.regimen),
                selectinload(Enterprise.classification),
                selectinload(Enterprise.document_type),
                selectinload(Enterprise.city),
                selectinload(Enterprise.liability_type),
            )
            .filter(Enterprise.en_id == enterprise_id)
        )
        return result.scalars().first()

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
        base_filter = []
        if search:
            base_filter.append(
                (Enterprise.en_name.ilike(f"%{search}%")) |
                (Enterprise.en_nit.ilike(f"%{search}%")) |
                (Enterprise.en_code.ilike(f"%{search}%"))
            )

        count_stmt = select(func.count()).select_from(Enterprise)
        if base_filter:
            count_stmt = count_stmt.where(*base_filter)
        total = (await db.execute(count_stmt)).scalar() or 0

        query = select(Enterprise).options(
            selectinload(Enterprise.regimen),
            selectinload(Enterprise.classification),
            selectinload(Enterprise.document_type),
            selectinload(Enterprise.city),
            selectinload(Enterprise.liability_type),
        )
        if base_filter:
            query = query.filter(*base_filter)

        result = await db.execute(query.offset(skip).limit(limit).order_by(Enterprise.en_name.asc()))
        return result.scalars().all(), total
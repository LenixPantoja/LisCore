from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.domains.compound_templates.domain.models import CompoundTemplate, TestCompoundTemplate


class CompoundTemplateRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> CompoundTemplate:
        template = CompoundTemplate(**data)
        db.add(template)
        await db.flush()
        return template

    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active_only: bool = False,
    ):
        query = select(CompoundTemplate)
        if active_only:
            query = query.where(CompoundTemplate.ct_active == True)
        if search:
            query = query.where(CompoundTemplate.ct_name.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(query.offset(skip).limit(limit).order_by(CompoundTemplate.ct_id.desc()))
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, ct_id: int) -> Optional[CompoundTemplate]:
        result = await db.execute(
            select(CompoundTemplate)
            .where(CompoundTemplate.ct_id == ct_id)
            .options(selectinload(CompoundTemplate.test_links))
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, ct_id: int, data: dict) -> Optional[CompoundTemplate]:
        template = await db.get(CompoundTemplate, ct_id)
        if not template:
            return None
        for key, value in data.items():
            setattr(template, key, value)
        await db.flush()
        return template

    @staticmethod
    async def delete(db: AsyncSession, ct_id: int) -> bool:
        template = await db.get(CompoundTemplate, ct_id)
        if not template:
            return False
        await db.delete(template)
        await db.flush()
        return True

    # ── N:M links ──────────────────────────────────────────────────────────────

    @staticmethod
    async def add_test_link(db: AsyncSession, ct_id: int, data: dict) -> TestCompoundTemplate:
        link = TestCompoundTemplate(tct_template_id=ct_id, **data)
        db.add(link)
        await db.flush()
        return link

    @staticmethod
    async def get_test_links(db: AsyncSession, ct_id: int) -> Sequence[TestCompoundTemplate]:
        result = await db.execute(
            select(TestCompoundTemplate)
            .where(TestCompoundTemplate.tct_template_id == ct_id)
            .order_by(TestCompoundTemplate.tct_order_index.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def update_test_link(db: AsyncSession, tct_id: int, data: dict) -> Optional[TestCompoundTemplate]:
        link = await db.get(TestCompoundTemplate, tct_id)
        if not link:
            return None
        for key, value in data.items():
            setattr(link, key, value)
        await db.flush()
        return link

    @staticmethod
    async def remove_test_link(db: AsyncSession, tct_id: int) -> bool:
        link = await db.get(TestCompoundTemplate, tct_id)
        if not link:
            return False
        await db.delete(link)
        await db.flush()
        return True

    @staticmethod
    async def get_templates_for_test(db: AsyncSession, test_id: int) -> Sequence[CompoundTemplate]:
        result = await db.execute(
            select(CompoundTemplate)
            .join(TestCompoundTemplate, TestCompoundTemplate.tct_template_id == CompoundTemplate.ct_id)
            .where(
                TestCompoundTemplate.tct_test_id == test_id,
                CompoundTemplate.ct_active == True,
            )
            .order_by(TestCompoundTemplate.tct_order_index.asc())
        )
        return result.scalars().all()
from typing import Optional, Sequence, Tuple

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.worksheets.domain.models import WorkSheet, WorkSheetStudy


class WorkSheetRepository:
    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        skip: int,
        limit: int,
        search: Optional[str] = None,
        active_only: bool = False,
        work_group_id: Optional[int] = None,
        headquarter_id: Optional[int] = None,
    ) -> Tuple[Sequence[WorkSheet], int]:
        query = select(WorkSheet)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(or_(WorkSheet.ws_name.ilike(term), WorkSheet.ws_description.ilike(term)))
        if active_only:
            query = query.where(WorkSheet.ws_active.is_(True))
        if work_group_id:
            query = query.where(WorkSheet.ws_work_group_id == work_group_id)
        if headquarter_id:
            # Las hojas sin sede aplican a todas
            query = query.where(or_(WorkSheet.ws_headquarter_id.is_(None), WorkSheet.ws_headquarter_id == headquarter_id))

        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
        result = await db.execute(query.order_by(WorkSheet.ws_name).offset(skip).limit(limit))
        return result.scalars().all(), total

    @staticmethod
    async def study_counts(db: AsyncSession, ws_ids: list[int]) -> dict[int, int]:
        if not ws_ids:
            return {}
        rows = await db.execute(
            select(WorkSheetStudy.wss_worksheet_id, func.count())
            .where(WorkSheetStudy.wss_worksheet_id.in_(ws_ids))
            .group_by(WorkSheetStudy.wss_worksheet_id)
        )
        return {ws_id: count for ws_id, count in rows.all()}

    @staticmethod
    async def get_by_id(db: AsyncSession, ws_id: int, with_studies: bool = False) -> Optional[WorkSheet]:
        query = select(WorkSheet).where(WorkSheet.ws_id == ws_id)
        if with_studies:
            query = query.options(selectinload(WorkSheet.study_links))
        return (await db.execute(query)).scalars().first()

    @staticmethod
    async def replace_studies(db: AsyncSession, ws_id: int, study_ids: list[int]) -> None:
        await db.execute(delete(WorkSheetStudy).where(WorkSheetStudy.wss_worksheet_id == ws_id))
        for order, study_id in enumerate(study_ids):
            db.add(WorkSheetStudy(wss_worksheet_id=ws_id, wss_study_id=study_id, wss_order=order))

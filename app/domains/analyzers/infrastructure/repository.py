from typing import Tuple, Sequence, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, date
from app.domains.analyzers.domain.models import Analyzer, AnalyzerGroup, AnalyzerDetail


class AnalyzerRepository:

    # ========== ANALYZER GROUPS ==========

    @staticmethod
    async def create_analyzer_group(db: AsyncSession, data: dict) -> AnalyzerGroup:
        """Create a new analyzer group"""
        group = AnalyzerGroup(**data)
        db.add(group)
        await db.commit()
        await db.refresh(group)
        return group

    @staticmethod
    async def get_analyzer_groups(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[AnalyzerGroup], int]:
        """Get analyzer groups with pagination"""
        query = select(AnalyzerGroup)

        if search:
            query = query.filter(AnalyzerGroup.ag_name.ilike(f"%{search}%"))
        if active is not None:
            query = query.filter(AnalyzerGroup.ag_active == active)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(AnalyzerGroup.ag_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_analyzer_group_by_id(db: AsyncSession, group_id: int) -> Optional[AnalyzerGroup]:
        """Get analyzer group by ID"""
        return await db.get(AnalyzerGroup, group_id)

    @staticmethod
    async def update_analyzer_group(db: AsyncSession, group_id: int, update_data: dict) -> Optional[AnalyzerGroup]:
        """Update an analyzer group"""
        group = await db.get(AnalyzerGroup, group_id)
        if not group:
            return None
        for key, value in update_data.items():
            setattr(group, key, value)
        await db.commit()
        await db.refresh(group)
        return group

    @staticmethod
    async def delete_analyzer_group(db: AsyncSession, group_id: int) -> dict:
        """Delete an analyzer group"""
        group = await db.get(AnalyzerGroup, group_id)
        if not group:
            return {"success": False, "message": "Grupo de analizador no encontrado"}
        await db.delete(group)
        await db.commit()
        return {"success": True, "message": "Grupo de analizador eliminado exitosamente"}

    # ========== ANALYZERS ==========

    @staticmethod
    async def create_analyzer(db: AsyncSession, data: dict) -> Analyzer:
        """Create a new analyzer"""
        now = datetime.utcnow()
        if 'a_created_at' not in data:
            data['a_created_at'] = now
        if 'a_updated_at' not in data:
            data['a_updated_at'] = now

        analyzer = Analyzer(**data)
        db.add(analyzer)
        await db.commit()
        await db.refresh(analyzer)

        # Reload with relationships
        result = await db.execute(
            select(Analyzer)
            .filter(Analyzer.a_id == analyzer.a_id)
            .options(
                selectinload(Analyzer.group),
                selectinload(Analyzer.work_group)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_analyzers(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        group_id: Optional[int] = None
    ) -> Tuple[Sequence[Analyzer], int]:
        """Get analyzers with pagination"""
        query = select(Analyzer).options(
            selectinload(Analyzer.group),
            selectinload(Analyzer.work_group)
        )

        if search:
            query = query.filter(Analyzer.a_name.ilike(f"%{search}%"))
        if active is not None:
            query = query.filter(Analyzer.a_active == active)
        if group_id is not None:
            query = query.filter(Analyzer.a_analyzer_group_id == group_id)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Analyzer.a_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_analyzer_by_id(db: AsyncSession, analyzer_id: int) -> Optional[Analyzer]:
        """Get analyzer by ID with relationships"""
        result = await db.execute(
            select(Analyzer)
            .filter(Analyzer.a_id == analyzer_id)
            .options(
                selectinload(Analyzer.group),
                selectinload(Analyzer.work_group),
                selectinload(Analyzer.details)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def update_analyzer(db: AsyncSession, analyzer_id: int, update_data: dict) -> Optional[Analyzer]:
        """Update an analyzer"""
        analyzer = await db.get(Analyzer, analyzer_id)
        if not analyzer:
            return None

        for key, value in update_data.items():
            setattr(analyzer, key, value)

        analyzer.a_updated_at = datetime.utcnow()

        await db.commit()

        result = await db.execute(
            select(Analyzer)
            .filter(Analyzer.a_id == analyzer_id)
            .options(
                selectinload(Analyzer.group),
                selectinload(Analyzer.work_group)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def delete_analyzer(db: AsyncSession, analyzer_id: int) -> dict:
        """Delete an analyzer"""
        analyzer = await db.get(Analyzer, analyzer_id)
        if not analyzer:
            return {"success": False, "message": "Analizador no encontrado"}
        await db.delete(analyzer)
        await db.commit()
        return {"success": True, "message": "Analizador eliminado exitosamente"}

    # ========== ANALYZER DETAILS ==========

    @staticmethod
    async def create_analyzer_detail(db: AsyncSession, data: dict) -> AnalyzerDetail:
        """Create a new analyzer detail"""
        if 'ad_created_at' not in data:
            data['ad_created_at'] = date.today()
        if 'ad_updated_at' not in data:
            data['ad_updated_at'] = date.today()

        detail = AnalyzerDetail(**data)
        db.add(detail)
        await db.commit()
        await db.refresh(detail)

        result = await db.execute(
            select(AnalyzerDetail)
            .filter(AnalyzerDetail.ad_id == detail.ad_id)
            .options(selectinload(AnalyzerDetail.test))
        )
        return result.scalars().first()

    @staticmethod
    async def get_analyzer_details(
        db: AsyncSession,
        analyzer_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[AnalyzerDetail], int]:
        """Get analyzer details with pagination"""
        from app.domains.testslabs.domain.models import TestsLab

        query = select(AnalyzerDetail).filter(
            AnalyzerDetail.ad_analyzer_id == analyzer_id
        ).options(selectinload(AnalyzerDetail.test))

        if search:
            query = query.join(
                TestsLab, AnalyzerDetail.ad_test_id == TestsLab.id, isouter=True
            ).filter(
                AnalyzerDetail.ad_transmission_code.ilike(f"%{search}%") |
                AnalyzerDetail.ad_sufix.ilike(f"%{search}%") |
                TestsLab.name.ilike(f"%{search}%") |
                TestsLab.code.ilike(f"%{search}%")
            )

        if active is not None:
            query = query.filter(AnalyzerDetail.ad_active == active)

        # Count query must replicate the same filters
        count_query = select(func.count()).select_from(AnalyzerDetail).filter(
            AnalyzerDetail.ad_analyzer_id == analyzer_id
        )
        if search:
            count_query = count_query.join(
                TestsLab, AnalyzerDetail.ad_test_id == TestsLab.id, isouter=True
            ).filter(
                AnalyzerDetail.ad_transmission_code.ilike(f"%{search}%") |
                AnalyzerDetail.ad_sufix.ilike(f"%{search}%") |
                TestsLab.name.ilike(f"%{search}%") |
                TestsLab.code.ilike(f"%{search}%")
            )
        if active is not None:
            count_query = count_query.filter(AnalyzerDetail.ad_active == active)

        total = (await db.execute(count_query)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(AnalyzerDetail.ad_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_analyzer_detail_by_id(db: AsyncSession, detail_id: int) -> Optional[AnalyzerDetail]:
        """Get analyzer detail by ID"""
        result = await db.execute(
            select(AnalyzerDetail)
            .filter(AnalyzerDetail.ad_id == detail_id)
            .options(selectinload(AnalyzerDetail.test))
        )
        return result.scalars().first()

    @staticmethod
    async def update_analyzer_detail(db: AsyncSession, detail_id: int, update_data: dict) -> Optional[AnalyzerDetail]:
        """Update an analyzer detail"""
        detail = await db.get(AnalyzerDetail, detail_id)
        if not detail:
            return None

        for key, value in update_data.items():
            setattr(detail, key, value)

        detail.ad_updated_at = date.today()

        await db.commit()

        result = await db.execute(
            select(AnalyzerDetail)
            .filter(AnalyzerDetail.ad_id == detail_id)
            .options(selectinload(AnalyzerDetail.test))
        )
        return result.scalars().first()

    @staticmethod
    async def delete_analyzer_detail(db: AsyncSession, detail_id: int) -> dict:
        """Delete an analyzer detail"""
        detail = await db.get(AnalyzerDetail, detail_id)
        if not detail:
            return {"success": False, "message": "Detalle de analizador no encontrado"}
        await db.delete(detail)
        await db.commit()
        return {"success": True, "message": "Detalle de analizador eliminado exitosamente"}

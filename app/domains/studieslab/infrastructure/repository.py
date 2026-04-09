from typing import List, Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail

class StudiesLabRepository:
    @staticmethod
    async def create(db: AsyncSession, data: dict) -> StudiesLab:
        new_study = StudiesLab(**data)
        db.add(new_study)
        await db.commit()
        await db.refresh(new_study)
        return new_study

    @staticmethod
    async def get_paginated(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None
    ) -> Tuple[Sequence[StudiesLab], int]:
        # 1. Base de la consulta
        query = select(StudiesLab).options(
            selectinload(StudiesLab.test_details)
            .selectinload(StudiesTestDetail.test),
            selectinload(StudiesLab.test_details)
            .selectinload(StudiesTestDetail.work_group),
            selectinload(StudiesLab.work_group)
        )
        
        # 2. Filtro de búsqueda (Opcional por nombre o código)
        if search:
            query = query.filter(
                (StudiesLab.name.ilike(f"%{search}%")) | 
                (StudiesLab.code.ilike(f"%{search}%"))
            )
        
        # 3. Contar total antes de paginar
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        # 4. Obtener ítems paginados
        result = await db.execute(query.offset(skip).limit(limit).order_by(StudiesLab.name.asc()))
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, study_id: int) -> Optional[StudiesLab]:
        result = await db.execute(
            select(StudiesLab)
            .filter(StudiesLab.id == study_id)
            .options(
                selectinload(StudiesLab.test_details)
                .selectinload(StudiesTestDetail.test),
                selectinload(StudiesLab.test_details)
                .selectinload(StudiesTestDetail.work_group),
                selectinload(StudiesLab.work_group)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, study_id: int, update_data: dict) -> Optional[StudiesLab]:
        study = await db.get(StudiesLab, study_id)
        if study:
            for key, value in update_data.items():
                setattr(study, key, value)
            await db.commit()
            await db.refresh(study)
        return study

    # --- Detalle de Exámenes ---
    @staticmethod
    async def add_test_detail(db: AsyncSession, study_id: int, detail_data: dict) -> StudiesTestDetail:
        detail = StudiesTestDetail(**detail_data, studies_id=study_id)
        db.add(detail)
        await db.commit()
        await db.refresh(detail)
        return detail

    @staticmethod
    async def remove_test_detail(db: AsyncSession, detail_id: int) -> bool:
        detail = await db.get(StudiesTestDetail, detail_id)
        if detail:
            await db.delete(detail)
            await db.commit()
            return True
        return False

    @staticmethod
    async def get_detail_by_id(db: AsyncSession, detail_id: int) -> Optional[StudiesTestDetail]:
        """Recupera un detalle de estudio con sus relaciones cargadas."""
        result = await db.execute(
            select(StudiesTestDetail)
            .filter(StudiesTestDetail.id == detail_id)
            .options(
                selectinload(StudiesTestDetail.test),
                selectinload(StudiesTestDetail.work_group)
            )
        )
        return result.scalars().first()
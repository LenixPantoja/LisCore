from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
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
    async def get_all(db: AsyncSession) -> List[StudiesLab]:
        result = await db.execute(
            select(StudiesLab).options(selectinload(StudiesLab.test_details))
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, study_id: int) -> Optional[StudiesLab]:
        result = await db.execute(
            select(StudiesLab)
            .filter(StudiesLab.id == study_id)
            .options(selectinload(StudiesLab.test_details))
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
from typing import List, Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.domains.testslabs.domain.models import TestsLab

class TestsLabRepository:
    @staticmethod
    async def create(db: AsyncSession, data: dict) -> TestsLab:
        new_test = TestsLab(**data)
        db.add(new_test)
        await db.flush()
        test_id = new_test.id
        await db.commit()
        return await TestsLabRepository.get_by_id(db, test_id)

    @staticmethod
    async def get_all(db: AsyncSession) -> List[TestsLab]:
        result = await db.execute(
            select(TestsLab).options(
                selectinload(TestsLab.technique),
                selectinload(TestsLab.work_group),
                selectinload(TestsLab.sample_type)
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_paginated(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None
    ) -> Tuple[Sequence[TestsLab], int]:
        # 1. Base de la consulta con relaciones cargadas
        query = select(TestsLab).options(
            selectinload(TestsLab.technique),
            selectinload(TestsLab.work_group),
            selectinload(TestsLab.sample_type)
        )
        
        # 2. Filtro de búsqueda
        if search:
            query = query.filter(
                (TestsLab.name.ilike(f"%{search}%")) | 
                (TestsLab.code.ilike(f"%{search}%"))
            )
        
        # 3. Conteo total antes de paginar
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        # 4. Resultados paginados
        result = await db.execute(query.offset(skip).limit(limit).order_by(TestsLab.name.asc()))
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, test_id: int) -> Optional[TestsLab]:
        result = await db.execute(
            select(TestsLab).filter(TestsLab.id == test_id).options(
                selectinload(TestsLab.technique),
                selectinload(TestsLab.work_group),
                selectinload(TestsLab.sample_type)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, test_id: int, update_data: dict) -> Optional[TestsLab]:
        test = await db.get(TestsLab, test_id)
        if not test:
            return None
        for key, value in update_data.items():
            setattr(test, key, value)
        await db.commit()
        return await TestsLabRepository.get_by_id(db, test_id)

    @staticmethod
    async def delete(db: AsyncSession, test_id: int) -> bool:
        test = await db.get(TestsLab, test_id)
        if test:
            await db.delete(test)
            await db.commit()
            return True
        return False
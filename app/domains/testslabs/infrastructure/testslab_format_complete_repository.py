from typing import List, Optional, Sequence, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.domains.testslabs.domain.models import FormatComplete, TestslabFormatComplete


class TestslabFormatCompleteRepository:

    @staticmethod
    async def get_default_results(db: AsyncSession, test_ids) -> Dict[int, str]:
        """
        Resultado predeterminado por prueba: el nombre del formato de completado
        marcado como predeterminado (y activo). {test_id: "Amarillo"}
        """
        ids = list({t for t in test_ids if t})
        if not ids:
            return {}
        rows = (await db.execute(
            select(TestslabFormatComplete.tfc_testslab_id, FormatComplete.fc_name)
            .join(FormatComplete, FormatComplete.fc_id == TestslabFormatComplete.tfc_format_complete_id)
            .where(
                TestslabFormatComplete.tfc_testslab_id.in_(ids),
                TestslabFormatComplete.tfc_is_default.is_(True),
                FormatComplete.fc_active.is_(True),
            )
            .order_by(TestslabFormatComplete.tfc_order_index.asc(), TestslabFormatComplete.tfc_id.asc())
        )).all()
        out: Dict[int, str] = {}
        for test_id, name in rows:
            if name and name.strip() and test_id not in out:
                out[test_id] = name.strip()
        return out

    @staticmethod
    async def clear_other_defaults(db: AsyncSession, testslab_id: int, keep_tfc_id: Optional[int] = None) -> None:
        """Una prueba tiene un solo formato predeterminado: desmarca los demás."""
        stmt = (update(TestslabFormatComplete)
                .where(TestslabFormatComplete.tfc_testslab_id == testslab_id,
                       TestslabFormatComplete.tfc_is_default.is_(True)))
        if keep_tfc_id is not None:
            stmt = stmt.where(TestslabFormatComplete.tfc_id != keep_tfc_id)
        await db.execute(stmt.values(tfc_is_default=False))

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> TestslabFormatComplete:
        record = TestslabFormatComplete(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        # Reload with related format_complete
        return await TestslabFormatCompleteRepository.get_by_id(db, record.tfc_id)

    @staticmethod
    async def get_by_testslab(
        db: AsyncSession, testslab_id: int
    ) -> Sequence[TestslabFormatComplete]:
        result = await db.execute(
            select(TestslabFormatComplete)
            .where(TestslabFormatComplete.tfc_testslab_id == testslab_id)
            .options(selectinload(TestslabFormatComplete.format_complete))
            .order_by(TestslabFormatComplete.tfc_order_index.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(
        db: AsyncSession, tfc_id: int
    ) -> Optional[TestslabFormatComplete]:
        result = await db.execute(
            select(TestslabFormatComplete)
            .where(TestslabFormatComplete.tfc_id == tfc_id)
            .options(selectinload(TestslabFormatComplete.format_complete))
        )
        return result.scalars().first()

    @staticmethod
    async def exists(
        db: AsyncSession, testslab_id: int, format_complete_id: int
    ) -> bool:
        result = await db.execute(
            select(TestslabFormatComplete.tfc_id).where(
                TestslabFormatComplete.tfc_testslab_id == testslab_id,
                TestslabFormatComplete.tfc_format_complete_id == format_complete_id,
            )
        )
        return result.scalar() is not None

    @staticmethod
    async def update(
        db: AsyncSession, tfc_id: int, data: dict
    ) -> Optional[TestslabFormatComplete]:
        record = await db.get(TestslabFormatComplete, tfc_id)
        if record:
            for key, value in data.items():
                setattr(record, key, value)
            await db.commit()
            return await TestslabFormatCompleteRepository.get_by_id(db, tfc_id)
        return None

    @staticmethod
    async def delete(db: AsyncSession, tfc_id: int) -> bool:
        record = await db.get(TestslabFormatComplete, tfc_id)
        if record:
            await db.delete(record)
            await db.commit()
            return True
        return False

    @staticmethod
    async def get_formats_by_testslab_ids(
        db: AsyncSession, testslab_ids: List[int]
    ) -> Dict[int, List[TestslabFormatComplete]]:
        """
        Batch query: returns a dict {testslab_id: [TestslabFormatComplete, ...]}
        sorted by tfc_order_index. Avoids N+1 queries.
        """
        if not testslab_ids:
            return {}
        result = await db.execute(
            select(TestslabFormatComplete)
            .where(TestslabFormatComplete.tfc_testslab_id.in_(testslab_ids))
            .options(selectinload(TestslabFormatComplete.format_complete))
            .order_by(
                TestslabFormatComplete.tfc_testslab_id,
                TestslabFormatComplete.tfc_order_index.asc(),
            )
        )
        rows = result.scalars().all()
        grouped: Dict[int, List[TestslabFormatComplete]] = {}
        for row in rows:
            grouped.setdefault(row.tfc_testslab_id, []).append(row)
        return grouped

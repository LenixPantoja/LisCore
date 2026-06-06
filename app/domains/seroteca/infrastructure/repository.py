from typing import Optional, Sequence, Tuple
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.seroteca.domain.models import SampleLog, Seroteca, Gradilla, GradillaPosicion
from app.domains.samples.domain.models import SamplesOrder
from utils.timezone import get_bogota_now


class SampleLogRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> SampleLog:
        log = SampleLog(**data)
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def get_by_sample(
        db: AsyncSession, so_id: int, skip: int = 0, limit: int = 100
    ) -> Tuple[Sequence[SampleLog], int]:
        count_q = select(func.count()).where(SampleLog.log_sample_order_id == so_id)
        total = (await db.execute(count_q)).scalar_one()

        q = (
            select(SampleLog)
            .where(SampleLog.log_sample_order_id == so_id)
            .options(
                selectinload(SampleLog.location),
                selectinload(SampleLog.user),
            )
            .order_by(SampleLog.log_create_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = (await db.execute(q)).scalars().all()
        return rows, total


class SerotecaRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> Seroteca:
        item = Seroteca(**data)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def get_by_id(db: AsyncSession, s_id: int) -> Optional[Seroteca]:
        return await db.get(Seroteca, s_id)

    @staticmethod
    async def list_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active_only: bool = False,
    ) -> Tuple[Sequence[Seroteca], int]:
        q = select(Seroteca)
        if search:
            q = q.where(Seroteca.s_name.ilike(f"%{search}%"))
        if active_only:
            q = q.where(Seroteca.s_active == True)

        total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        rows = (await db.execute(q.offset(skip).limit(limit).order_by(Seroteca.s_name.asc()))).scalars().all()
        return rows, total

    @staticmethod
    async def update(db: AsyncSession, s_id: int, data: dict) -> Optional[Seroteca]:
        item = await db.get(Seroteca, s_id)
        if not item:
            return None
        for k, v in data.items():
            setattr(item, k, v)
        item.s_updated_at = get_bogota_now()
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def delete(db: AsyncSession, s_id: int) -> bool:
        item = await db.get(Seroteca, s_id)
        if not item:
            return False
        await db.delete(item)
        await db.commit()
        return True


class GradillaRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> Gradilla:
        rack = Gradilla(**data)
        db.add(rack)
        await db.flush()  # get rack.g_id before generating positions

        # Auto-generate all positions (rows × cols)
        positions = [
            GradillaPosicion(gp_gradilla_id=rack.g_id, gp_row=r, gp_col=c)
            for r in range(rack.g_rows)
            for c in range(rack.g_cols)
        ]
        db.add_all(positions)
        await db.commit()
        await db.refresh(rack)
        return rack

    @staticmethod
    async def get_by_id(db: AsyncSession, g_id: int) -> Optional[Gradilla]:
        sample_loader = selectinload(GradillaPosicion.sample)
        q = (
            select(Gradilla)
            .where(Gradilla.g_id == g_id)
            .options(
                selectinload(Gradilla.positions).options(
                    sample_loader.selectinload(SamplesOrder.order),
                    sample_loader.selectinload(SamplesOrder.sample_type),
                )
            )
        )
        return (await db.execute(q)).scalars().first()

    @staticmethod
    async def list_by_seroteca(
        db: AsyncSession, s_id: int, skip: int = 0, limit: int = 100
    ) -> Tuple[Sequence[Gradilla], int]:
        q = select(Gradilla).where(Gradilla.g_seroteca_id == s_id)
        total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        rows = (
            await db.execute(q.offset(skip).limit(limit).order_by(Gradilla.g_name.asc()))
        ).scalars().all()
        return rows, total

    @staticmethod
    async def update(db: AsyncSession, g_id: int, data: dict) -> Optional[Gradilla]:
        rack = await db.get(Gradilla, g_id)
        if not rack:
            return None
        for k, v in data.items():
            setattr(rack, k, v)
        rack.g_updated_at = get_bogota_now()
        await db.commit()
        await db.refresh(rack)
        return rack

    @staticmethod
    async def delete(db: AsyncSession, g_id: int) -> bool:
        rack = await db.get(Gradilla, g_id)
        if not rack:
            return False
        await db.delete(rack)
        await db.commit()
        return True


class GradillaPosicionRepository:

    @staticmethod
    async def get_next_free(db: AsyncSession, g_id: int) -> Optional[GradillaPosicion]:
        """Return the first unoccupied position in a rack, ordered row then col."""
        q = (
            select(GradillaPosicion)
            .where(
                GradillaPosicion.gp_gradilla_id == g_id,
                GradillaPosicion.gp_occupied == False,
            )
            .order_by(GradillaPosicion.gp_row.asc(), GradillaPosicion.gp_col.asc())
            .limit(1)
        )
        return (await db.execute(q)).scalars().first()

    @staticmethod
    async def get_by_id(db: AsyncSession, gp_id: int) -> Optional[GradillaPosicion]:
        return await db.get(GradillaPosicion, gp_id)

    @staticmethod
    async def store_sample(
        db: AsyncSession, gp_id: int, so_id: int, user_id: Optional[int]
    ) -> Optional[GradillaPosicion]:
        pos = await db.get(GradillaPosicion, gp_id)
        if not pos or pos.gp_occupied:
            return None
        pos.gp_sample_id = so_id
        pos.gp_occupied = True
        pos.gp_stored_at = get_bogota_now()
        pos.gp_stored_by_id = user_id
        await db.flush()
        # Eagerly load the sample relationship and nested relations to avoid MissingGreenlet on serialization
        result = await db.execute(
            select(GradillaPosicion)
            .where(GradillaPosicion.gp_id == gp_id)
            .options(
                selectinload(GradillaPosicion.sample).options(
                    selectinload(SamplesOrder.order),
                    selectinload(SamplesOrder.sample_type),
                )
            )
        )
        pos = result.scalars().first()
        await db.commit()
        return pos

    @staticmethod
    async def release_position(db: AsyncSession, gp_id: int) -> Optional[GradillaPosicion]:
        pos = await db.get(GradillaPosicion, gp_id)
        if not pos or not pos.gp_occupied:
            return None
        pos.gp_sample_id = None
        pos.gp_occupied = False
        pos.gp_stored_at = None
        pos.gp_stored_by_id = None
        await db.flush()
        # Eagerly load the sample relationship and nested relations to avoid MissingGreenlet on serialization
        result = await db.execute(
            select(GradillaPosicion)
            .where(GradillaPosicion.gp_id == gp_id)
            .options(
                selectinload(GradillaPosicion.sample).options(
                    selectinload(SamplesOrder.order),
                    selectinload(SamplesOrder.sample_type),
                )
            )
        )
        pos = result.scalars().first()
        await db.commit()
        return pos

from typing import Optional, Sequence, Tuple
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.seroteca.domain.models import SampleLog, Seroteca, Gradilla, GradillaPosicion, TipoGradilla
from app.domains.samples.domain.models import SamplesOrder
from app.domains.orders.domain.models import Order
from utils.timezone import get_bogota_now
from utils.Consecutives.consecutive_gradillas import generate_gradilla_number


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
                selectinload(SampleLog.sample).selectinload(SamplesOrder.order),
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
        # Recargar con relaciones eager-loaded para evitar MissingGreenlet
        result = await db.execute(
            select(Seroteca)
            .where(Seroteca.s_id == item.s_id)
            .options(
                selectinload(Seroteca.location),
                selectinload(Seroteca.headquarter),
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_id(db: AsyncSession, s_id: int) -> Optional[Seroteca]:
        q = (
            select(Seroteca)
            .where(Seroteca.s_id == s_id)
            .options(
                selectinload(Seroteca.location),
                selectinload(Seroteca.headquarter),
            )
        )
        result = await db.execute(q)
        return result.scalars().first()

    @staticmethod
    async def list_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active_only: bool = False,
        headquarter_id: Optional[int] = None,
    ) -> Tuple[Sequence[Seroteca], int]:
        q = select(Seroteca).options(
            selectinload(Seroteca.location),
            selectinload(Seroteca.headquarter),
        )
        if search:
            q = q.where(Seroteca.s_name.ilike(f"%{search}%"))
        if active_only:
            q = q.where(Seroteca.s_active == True)
        if headquarter_id is not None:
            q = q.where(Seroteca.s_headquarter_id == headquarter_id)

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
        # Recargar con relaciones eager-loaded
        result = await db.execute(
            select(Seroteca)
            .where(Seroteca.s_id == s_id)
            .options(
                selectinload(Seroteca.location),
                selectinload(Seroteca.headquarter),
            )
        )
        return result.scalars().first()

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
                    sample_loader.selectinload(SamplesOrder.order)
                        .selectinload(Order.patient),
                    sample_loader.selectinload(SamplesOrder.sample_type),
                )
            )
        )
        return (await db.execute(q)).scalars().first()

    @staticmethod
    async def list_by_seroteca(
        db: AsyncSession, s_id: int, skip: int = 0, limit: int = 100, search: Optional[str] = None
    ) -> Tuple[Sequence[Gradilla], int]:
        q = select(Gradilla).where(Gradilla.g_seroteca_id == s_id)
        if search:
            q = q.where(
                (Gradilla.g_name.ilike(f"%{search}%")) |
                (Gradilla.g_number.ilike(f"%{search}%"))
            )
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
    async def is_sample_stored(db: AsyncSession, so_id: int) -> Optional[GradillaPosicion]:
        """Check if a sample is already stored in any position. Returns the position if found."""
        q = (
            select(GradillaPosicion)
            .where(
                GradillaPosicion.gp_sample_id == so_id,
                GradillaPosicion.gp_occupied == True,
            )
            .limit(1)
        )
        result = await db.execute(q)
        return result.scalars().first()

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
                    selectinload(SamplesOrder.order).selectinload(Order.patient),
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
                    selectinload(SamplesOrder.order).selectinload(Order.patient),
                    selectinload(SamplesOrder.sample_type),
                )
            )
        )
        pos = result.scalars().first()
        await db.commit()
        return pos


class TipoGradillaRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> TipoGradilla:
        item = TipoGradilla(**data)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def get_by_id(db: AsyncSession, tg_id: int) -> Optional[TipoGradilla]:
        return await db.get(TipoGradilla, tg_id)

    @staticmethod
    async def list_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active_only: bool = False,
    ) -> Tuple[Sequence[TipoGradilla], int]:
        q = select(TipoGradilla)
        if search:
            q = q.where(TipoGradilla.tg_name.ilike(f"%{search}%"))
        if active_only:
            q = q.where(TipoGradilla.tg_active == True)

        total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        rows = (await db.execute(q.offset(skip).limit(limit).order_by(TipoGradilla.tg_name.asc()))).scalars().all()
        return rows, total

    @staticmethod
    async def update(db: AsyncSession, tg_id: int, data: dict) -> Optional[TipoGradilla]:
        item = await db.get(TipoGradilla, tg_id)
        if not item:
            return None
        for k, v in data.items():
            setattr(item, k, v)
        item.tg_updated_at = get_bogota_now()
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def delete(db: AsyncSession, tg_id: int) -> bool:
        item = await db.get(TipoGradilla, tg_id)
        if not item:
            return False
        await db.delete(item)
        await db.commit()
        return True
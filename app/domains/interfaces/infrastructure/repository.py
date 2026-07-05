from typing import Tuple, Sequence, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from datetime import datetime
from app.domains.interfaces.domain.models import InterfacesRest, InterfacesRestDetail
from app.domains.enterprises.domain.models import Enterprise


class InterfacesRestRepository:

    # ========== INTERFACES REST ==========

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> InterfacesRest:
        """Create a new interface REST"""
        now = datetime.utcnow()
        if 'it_created_at' not in data:
            data['it_created_at'] = now
        if 'it_updated_at' not in data:
            data['it_updated_at'] = now

        obj = InterfacesRest(**data)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)

        result = await db.execute(
            select(InterfacesRest)
            .filter(InterfacesRest.it_id == obj.it_id)
            .options(
                selectinload(InterfacesRest.enterprise),
                selectinload(InterfacesRest.tariff)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        state: Optional[bool] = None,
        enterprise_id: Optional[int] = None
    ) -> Tuple[Sequence[InterfacesRest], int]:
        """Get interfaces REST with pagination"""
        query = (
            select(InterfacesRest)
            .join(Enterprise, InterfacesRest.it_enterprise_id == Enterprise.en_id, isouter=True)
            .options(
                selectinload(InterfacesRest.enterprise),
                selectinload(InterfacesRest.tariff),
            )
        )

        if state is not None:
            query = query.filter(InterfacesRest.it_state == state)
        if enterprise_id is not None:
            query = query.filter(InterfacesRest.it_enterprise_id == enterprise_id)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Enterprise.en_name.ilike(pattern),
                    Enterprise.en_nit.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(InterfacesRest.it_id.asc())
        )
        return result.scalars().unique().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, interface_id: int) -> Optional[InterfacesRest]:
        """Get interface REST by ID with relationships"""
        result = await db.execute(
            select(InterfacesRest)
            .filter(InterfacesRest.it_id == interface_id)
            .options(
                selectinload(InterfacesRest.enterprise),
                selectinload(InterfacesRest.tariff),
                selectinload(InterfacesRest.details)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, interface_id: int, update_data: dict) -> Optional[InterfacesRest]:
        """Update an interface REST"""
        obj = await db.get(InterfacesRest, interface_id)
        if not obj:
            return None

        for key, value in update_data.items():
            setattr(obj, key, value)

        obj.it_updated_at = datetime.utcnow()

        await db.commit()

        result = await db.execute(
            select(InterfacesRest)
            .filter(InterfacesRest.it_id == interface_id)
            .options(
                selectinload(InterfacesRest.enterprise),
                selectinload(InterfacesRest.tariff)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def delete(db: AsyncSession, interface_id: int) -> dict:
        """Delete an interface REST"""
        obj = await db.get(InterfacesRest, interface_id)
        if not obj:
            return {"success": False, "message": "Interfaz REST no encontrada"}
        await db.delete(obj)
        await db.commit()
        return {"success": True, "message": "Interfaz REST eliminada exitosamente"}

    # ========== INTERFACES REST DETAILS ==========

    @staticmethod
    async def create_detail(db: AsyncSession, data: dict) -> InterfacesRestDetail:
        """Create a new interface REST detail"""
        if 'itd_created_at' not in data:
            data['itd_created_at'] = datetime.utcnow()
        if 'itd_updated_at' not in data:
            data['itd_updated_at'] = datetime.utcnow()

        obj = InterfacesRestDetail(**data)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)

        result = await db.execute(
            select(InterfacesRestDetail)
            .filter(InterfacesRestDetail.itd_id == obj.itd_id)
            .options(selectinload(InterfacesRestDetail.study))
        )
        return result.scalars().first()

    @staticmethod
    async def get_details_paginated(
        db: AsyncSession,
        interface_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> Tuple[Sequence[InterfacesRestDetail], int]:
        """Get interface REST details with pagination"""
        from app.domains.studieslab.domain.models import StudiesLab

        query = select(InterfacesRestDetail).filter(
            InterfacesRestDetail.itd_interface_rest_id == interface_id
        ).options(selectinload(InterfacesRestDetail.study))

        if search:
            query = query.join(
                StudiesLab, InterfacesRestDetail.itd_study_id == StudiesLab.id, isouter=True
            ).filter(
                InterfacesRestDetail.itd_send_code.ilike(f"%{search}%") |
                InterfacesRestDetail.itd_receipt_code.ilike(f"%{search}%") |
                StudiesLab.name.ilike(f"%{search}%") |
                StudiesLab.code.ilike(f"%{search}%")
            )

        # Count query must replicate the same filters
        count_stmt = select(func.count()).select_from(InterfacesRestDetail).filter(
            InterfacesRestDetail.itd_interface_rest_id == interface_id
        )
        if search:
            count_stmt = count_stmt.join(
                StudiesLab, InterfacesRestDetail.itd_study_id == StudiesLab.id, isouter=True
            ).filter(
                InterfacesRestDetail.itd_send_code.ilike(f"%{search}%") |
                InterfacesRestDetail.itd_receipt_code.ilike(f"%{search}%") |
                StudiesLab.name.ilike(f"%{search}%") |
                StudiesLab.code.ilike(f"%{search}%")
            )
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(InterfacesRestDetail.itd_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_detail_by_id(db: AsyncSession, detail_id: int) -> Optional[InterfacesRestDetail]:
        """Get interface REST detail by ID"""
        result = await db.execute(
            select(InterfacesRestDetail)
            .filter(InterfacesRestDetail.itd_id == detail_id)
            .options(selectinload(InterfacesRestDetail.study))
        )
        return result.scalars().first()

    @staticmethod
    async def update_detail(db: AsyncSession, detail_id: int, update_data: dict) -> Optional[InterfacesRestDetail]:
        """Update an interface REST detail"""
        obj = await db.get(InterfacesRestDetail, detail_id)
        if not obj:
            return None

        for key, value in update_data.items():
            setattr(obj, key, value)

        obj.itd_updated_at = datetime.utcnow()

        await db.commit()

        result = await db.execute(
            select(InterfacesRestDetail)
            .filter(InterfacesRestDetail.itd_id == detail_id)
            .options(selectinload(InterfacesRestDetail.study))
        )
        return result.scalars().first()

    @staticmethod
    async def delete_detail(db: AsyncSession, detail_id: int) -> dict:
        """Delete an interface REST detail"""
        obj = await db.get(InterfacesRestDetail, detail_id)
        if not obj:
            return {"success": False, "message": "Detalle de interfaz REST no encontrado"}
        await db.delete(obj)
        await db.commit()
        return {"success": True, "message": "Detalle de interfaz REST eliminado exitosamente"}

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.medics.domain.models import Medic


class MedicRepository:
    @staticmethod
    async def get(db: AsyncSession, med_id: int) -> Optional[Medic]:
        return await db.get(Medic, med_id)

    @staticmethod
    def _filters(search: Optional[str], codigo: Optional[str], name: Optional[str]) -> list:
        """
        Filtros de búsqueda de médicos:
          - codigo: código del médico exacto (med_codigo, sin importar mayúsculas).
          - name:   nombre, coincidencia parcial sin importar mayúsculas.
          - search: texto libre: código exacto, o parcial en nombre, documento,
                    especialidad, tarjeta profesional y usuario.
        """
        conds = []
        if codigo and codigo.strip():
            conds.append(func.lower(Medic.med_codigo) == codigo.strip().lower())
        if name and name.strip():
            conds.append(Medic.med_name.ilike(f"%{name.strip()}%"))
        if search and search.strip():
            text = search.strip()
            term = f"%{text}%"
            conds.append(or_(
                func.lower(Medic.med_codigo) == text.lower(),
                Medic.med_name.ilike(term),
                Medic.med_document_number.ilike(term),
                Medic.med_specialty.ilike(term),
                Medic.med_card_professional_number.ilike(term),
                Medic.med_user.ilike(term),
            ))
        return conds

    @staticmethod
    async def list_paged(
        db: AsyncSession,
        skip: int,
        limit: int,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        codigo: Optional[str] = None,
        name: Optional[str] = None,
    ) -> tuple[list[Medic], int]:
        stmt = select(Medic).where(*MedicRepository._filters(search, codigo, name))
        if is_active is not None:
            stmt = stmt.where(Medic.med_is_active.is_(is_active))
        total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await db.execute(stmt.order_by(Medic.med_name).offset(skip).limit(limit))).scalars().all()
        return list(rows), total

    @staticmethod
    async def list_active(
        db: AsyncSession,
        search: Optional[str] = None,
        codigo: Optional[str] = None,
        name: Optional[str] = None,
    ) -> list[Medic]:
        stmt = (
            select(Medic)
            .where(Medic.med_is_active.is_(True), Medic.med_is_locked.is_(False))
            .where(*MedicRepository._filters(search, codigo, name))
            .order_by(Medic.med_name)
        )
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def user_taken(db: AsyncSession, user: str, exclude_id: Optional[int] = None) -> bool:
        stmt = select(Medic.med_id).where(func.lower(Medic.med_user) == user.lower())
        if exclude_id is not None:
            stmt = stmt.where(Medic.med_id != exclude_id)
        return (await db.execute(stmt)).first() is not None

    @staticmethod
    async def codigo_taken(db: AsyncSession, codigo: str, exclude_id: Optional[int] = None) -> bool:
        stmt = select(Medic.med_id).where(func.lower(Medic.med_codigo) == codigo.lower())
        if exclude_id is not None:
            stmt = stmt.where(Medic.med_id != exclude_id)
        return (await db.execute(stmt)).first() is not None

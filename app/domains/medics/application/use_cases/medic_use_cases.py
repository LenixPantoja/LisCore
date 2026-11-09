from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.domains.medics.domain.models import Medic
from app.domains.medics.infrastructure.repository import MedicRepository


def _to_dict(m: Medic) -> dict:
    return {
        "med_codigo": m.med_codigo,
        "med_name": m.med_name,
        "med_document_number": m.med_document_number,
        "med_specialty": m.med_specialty,
        "med_card_professional_number": m.med_card_professional_number,
        "med_phone": m.med_phone,
        "med_mail": m.med_mail,
        "med_user": m.med_user,
        "med_has_password": bool(m.med_password),
        "med_reset_password": bool(m.med_reset_password),
        "med_is_locked": bool(m.med_is_locked),
        "med_is_active": bool(m.med_is_active),
        "med_created_at": m.med_created_at,
        "med_updated_at": m.med_updated_at,
    }


async def _get_or_404(db: AsyncSession, med_codigo: int) -> Medic:
    medic = await MedicRepository.get(db, med_codigo)
    if not medic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médico no encontrado.")
    return medic


async def list_medics(
    db: AsyncSession, skip: int, limit: int, search: Optional[str], is_active: Optional[bool],
    codigo: Optional[int] = None, name: Optional[str] = None,
) -> dict:
    rows, total = await MedicRepository.list_paged(db, skip, limit, search, is_active, codigo, name)
    return {"total": total, "skip": skip, "limit": limit, "items": [_to_dict(m) for m in rows]}


async def list_active_medics(
    db: AsyncSession, search: Optional[str] = None, codigo: Optional[int] = None, name: Optional[str] = None,
) -> list[dict]:
    rows = await MedicRepository.list_active(db, search, codigo, name)
    return [
        {"med_codigo": m.med_codigo, "med_name": m.med_name, "med_document_number": m.med_document_number,
         "med_specialty": m.med_specialty, "med_card_professional_number": m.med_card_professional_number}
        for m in rows
    ]


async def get_medic(db: AsyncSession, med_codigo: int) -> dict:
    return _to_dict(await _get_or_404(db, med_codigo))


async def create_medic(db: AsyncSession, data: dict) -> dict:
    if data.get("med_user") and await MedicRepository.user_taken(db, data["med_user"]):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"El usuario '{data['med_user']}' ya está asignado a otro médico.")
    password = data.pop("med_password", None)
    medic = Medic(**data)
    if password:
        medic.med_password = get_password_hash(password)
    db.add(medic)
    await db.commit()
    await db.refresh(medic)
    return _to_dict(medic)


async def update_medic(db: AsyncSession, med_codigo: int, data: dict) -> dict:
    medic = await _get_or_404(db, med_codigo)
    if data.get("med_user") and await MedicRepository.user_taken(db, data["med_user"], exclude_codigo=med_codigo):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"El usuario '{data['med_user']}' ya está asignado a otro médico.")
    password = data.pop("med_password", None)
    for key, value in data.items():
        # Campos no anulables: un null explícito no los borra
        if value is None and key in ("med_name", "med_reset_password", "med_is_locked", "med_is_active"):
            continue
        setattr(medic, key, value)
    if password:
        medic.med_password = get_password_hash(password)
    await db.commit()
    await db.refresh(medic)
    return _to_dict(medic)


async def delete_medic(db: AsyncSession, med_codigo: int) -> dict:
    """Elimina el médico. Si ya tiene órdenes asociadas no se borra: se debe inactivar."""
    from app.domains.orders.domain.models import Order

    medic = await _get_or_404(db, med_codigo)
    orders = (await db.execute(select(func.count(Order.o_id)).where(Order.o_medic_id == med_codigo))).scalar() or 0
    if orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El médico tiene {orders} orden(es) asociada(s) y no se puede eliminar. Inactívelo en su lugar.",
        )
    await db.delete(medic)
    await db.commit()
    return {"success": True, "message": "Médico eliminado."}

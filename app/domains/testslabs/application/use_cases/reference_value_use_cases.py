from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.domains.testslabs.infrastructure.reference_value_repository import ReferenceValueRepository
from app.domains.testslabs.infrastructure.ranges_reference_repository import RangesReferenceRepository


async def create_reference_value(db: AsyncSession, ranges_references_id: int, data: dict) -> dict:
    range_ref = await RangesReferenceRepository.get_by_id(db, ranges_references_id)
    if not range_ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El rango de referencia no existe.",
        )
    data["ranges_references_id"] = ranges_references_id
    return await ReferenceValueRepository.create(db, data)


async def list_reference_values_by_range(db: AsyncSession, ranges_references_id: int) -> dict:
    range_ref = await RangesReferenceRepository.get_by_id(db, ranges_references_id)
    if not range_ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El rango de referencia no existe.",
        )
    items, total = await ReferenceValueRepository.get_all_by_range(db, ranges_references_id)
    return {"total": total, "items": items}


async def get_reference_value(db: AsyncSession, value_id: int):
    instance = await ReferenceValueRepository.get_by_id(db, value_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valor de referencia no encontrado.",
        )
    return instance


async def update_reference_value(db: AsyncSession, value_id: int, data: dict):
    instance = await ReferenceValueRepository.update(db, value_id, data)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valor de referencia no encontrado.",
        )
    return instance


async def delete_reference_value(db: AsyncSession, value_id: int) -> dict:
    deleted = await ReferenceValueRepository.delete(db, value_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valor de referencia no encontrado.",
        )
    return {"message": "Valor de referencia eliminado correctamente."}

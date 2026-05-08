from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.domains.testslabs.infrastructure.ranges_reference_repository import RangesReferenceRepository
from app.domains.testslabs.infrastructure.repository import TestsLabRepository


async def create_range_reference(db: AsyncSession, test_id: int, data: dict) -> dict:
    test = await TestsLabRepository.get_by_id(db, test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La prueba de laboratorio no existe.",
        )
    data["test_id"] = test_id
    return await RangesReferenceRepository.create(db, data)


async def list_ranges_references_by_test(db: AsyncSession, test_id: int) -> dict:
    test = await TestsLabRepository.get_by_id(db, test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La prueba de laboratorio no existe.",
        )
    items, total = await RangesReferenceRepository.get_all_by_test(db, test_id)
    return {"total": total, "items": items}


async def get_range_reference(db: AsyncSession, range_id: int):
    instance = await RangesReferenceRepository.get_by_id(db, range_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rango de referencia no encontrado.",
        )
    return instance


async def update_range_reference(db: AsyncSession, range_id: int, data: dict):
    instance = await RangesReferenceRepository.update(db, range_id, data)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rango de referencia no encontrado.",
        )
    return instance


async def delete_range_reference(db: AsyncSession, range_id: int) -> dict:
    deleted = await RangesReferenceRepository.delete(db, range_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rango de referencia no encontrado.",
        )
    return {"message": "Rango de referencia eliminado correctamente."}

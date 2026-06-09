from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.domains.testslabs.infrastructure.testslab_format_complete_repository import (
    TestslabFormatCompleteRepository,
)
from app.domains.testslabs.infrastructure.repository import TestsLabRepository
from app.domains.testslabs.infrastructure.format_complete_repository import FormatCompleteRepository


async def link_format_to_testslab(db: AsyncSession, testslab_id: int, data: dict):
    # Validate testslab exists
    if not await TestsLabRepository.get_by_id(db, testslab_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prueba de laboratorio no encontrada.",
        )
    # Validate format exists
    if not await FormatCompleteRepository.get_by_id(db, data["tfc_format_complete_id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formato no encontrado.",
        )
    # Prevent duplicates
    if await TestslabFormatCompleteRepository.exists(db, testslab_id, data["tfc_format_complete_id"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El formato ya está vinculado a esta prueba.",
        )
    try:
        payload = {**data, "tfc_testslab_id": testslab_id}
        return await TestslabFormatCompleteRepository.create(db, payload)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al vincular el formato.",
        )


async def list_formats_by_testslab(db: AsyncSession, testslab_id: int):
    items = await TestslabFormatCompleteRepository.get_by_testslab(db, testslab_id)
    return {"total": len(items), "items": items}


async def get_link_by_id(db: AsyncSession, tfc_id: int):
    record = await TestslabFormatCompleteRepository.get_by_id(db, tfc_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vínculo no encontrado.",
        )
    return record


async def update_link(db: AsyncSession, tfc_id: int, data: dict):
    record = await TestslabFormatCompleteRepository.update(db, tfc_id, data)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vínculo no encontrado.",
        )
    return record


async def unlink_format_from_testslab(db: AsyncSession, tfc_id: int):
    if not await TestslabFormatCompleteRepository.delete(db, tfc_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vínculo no encontrado.",
        )
    return {"message": "Vínculo eliminado correctamente."}

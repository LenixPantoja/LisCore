from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.domains.testslabs.infrastructure.format_complete_repository import FormatCompleteRepository


async def create_format(db: AsyncSession, data: dict):
    try:
        return await FormatCompleteRepository.create(db, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al crear el formato.",
        )


async def list_formats(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None):
    items, total = await FormatCompleteRepository.get_all(db, skip, limit, search)
    return {"total": total, "items": items}


async def get_format_by_id(db: AsyncSession, fc_id: int):
    record = await FormatCompleteRepository.get_by_id(db, fc_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formato no encontrado.",
        )
    return record


async def update_format(db: AsyncSession, fc_id: int, data: dict):
    record = await FormatCompleteRepository.update(db, fc_id, data)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formato no encontrado.",
        )
    return record


async def delete_format(db: AsyncSession, fc_id: int):
    if not await FormatCompleteRepository.delete(db, fc_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formato no encontrado.",
        )
    return {"message": "Formato eliminado correctamente."}

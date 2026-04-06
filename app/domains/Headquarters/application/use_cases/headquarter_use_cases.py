from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.Headquarters.infrastructure.repository import HeadquarterRepository
from fastapi import HTTPException, status

async def create_hq(db: AsyncSession, data: dict):
    return await HeadquarterRepository.create(db, data)

async def list_hqs(db: AsyncSession):
    return await HeadquarterRepository.get_all(db)

async def get_hq_by_id(db: AsyncSession, hq_id: int):
    hq = await HeadquarterRepository.get_by_id(db, hq_id)
    if not hq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sede no encontrada")
    return hq

async def update_hq(db: AsyncSession, hq_id: int, data: dict):
    hq = await HeadquarterRepository.update(db, hq_id, data)
    if not hq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sede no encontrada")
    return hq

async def delete_hq(db: AsyncSession, hq_id: int):
    success = await HeadquarterRepository.delete(db, hq_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sede no encontrada")
    return {"message": "Sede eliminada correctamente"}
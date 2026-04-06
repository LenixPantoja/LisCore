from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.samples.infrastructure.repository import SampleRepository
from fastapi import HTTPException, status

async def list_sample_types(db: AsyncSession):
    return await SampleRepository.get_all_types(db)

async def create_sample_type(db: AsyncSession, data: dict):
    return await SampleRepository.create_type(db, data)

async def get_sample_type_by_id(db: AsyncSession, st_id: int):
    item = await SampleRepository.get_type_by_id(db, st_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de muestra no encontrado")
    return item

async def update_sample_type(db: AsyncSession, st_id: int, data: dict):
    item = await SampleRepository.update_type(db, st_id, data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de muestra no encontrado")
    return item

async def delete_sample_type(db: AsyncSession, st_id: int):
    success = await SampleRepository.delete_type(db, st_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de muestra no encontrado")
    return {"message": "Tipo de muestra eliminado correctamente"}
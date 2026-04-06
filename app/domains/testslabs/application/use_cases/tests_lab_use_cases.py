from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.testslabs.infrastructure.repository import TestsLabRepository
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

async def create_test(db: AsyncSession, data: dict):
    try:
        return await TestsLabRepository.create(db, data)
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig)
        if "technical_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La técnica seleccionada no existe.")
        if "work_group_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El grupo de trabajo seleccionado no existe.")
        if "samples_type_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El tipo de muestra seleccionado no existe.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error de integridad al crear el examen.")

async def list_tests(db: AsyncSession):
    return await TestsLabRepository.get_all(db)

async def get_test_by_id(db: AsyncSession, test_id: int):
    test = await TestsLabRepository.get_by_id(db, test_id)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen no encontrado")
    return test

async def update_test(db: AsyncSession, test_id: int, data: dict):
    try:
        test = await TestsLabRepository.update(db, test_id, data)
        if not test:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen no encontrado")
        return test
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error al actualizar el examen.")

async def delete_test(db: AsyncSession, test_id: int):
    if not await TestsLabRepository.delete(db, test_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen no encontrado")
    return {"message": "Examen eliminado correctamente"}
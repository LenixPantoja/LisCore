from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.studieslab.infrastructure.repository import StudiesLabRepository
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

async def create_study(db: AsyncSession, data: dict):
    try:
        new_study = await StudiesLabRepository.create(db, data)
        return await StudiesLabRepository.get_by_id(db, new_study.id)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Error de integridad al crear el estudio. Verifique que el código no esté duplicado."
        )

async def add_test_to_study(db: AsyncSession, study_id: int, detail_data: dict):
    try:
        # 1. Verificar si el estudio existe
        study = await StudiesLabRepository.get_by_id(db, study_id)
        if not study:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudio no encontrado")
            
        # 2. Agregar el detalle
        new_detail = await StudiesLabRepository.add_test_detail(db, study_id, detail_data)
        
        # 3. Retornar el detalle con relaciones cargadas
        return await StudiesLabRepository.get_detail_by_id(db, new_detail.id)
        
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig)
        if "StudiesTestDetail_pkey" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error de secuencia en la base de datos (ID duplicado). Por favor sincronice las secuencias de la tabla StudiesTestDetail."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo agregar la prueba al estudio. Verifique los IDs de prueba y grupo de trabajo."
        )

async def update_test_detail(db: AsyncSession, detail_id: int, update_data: dict):
    try:
        detail = await StudiesLabRepository.update_test_detail(db, detail_id, update_data)
        if not detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detalle no encontrado")
        return await StudiesLabRepository.get_detail_by_id(db, detail.id)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error al actualizar el detalle de la prueba.")

async def list_studies(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None):
    items, total = await StudiesLabRepository.get_paginated(db, skip, limit, search)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }
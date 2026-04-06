from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.masters.infrastructure.repository import MastersRepository
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

async def create_item(db: AsyncSession, model, data: dict):
    try:
        return await MastersRepository.create_master(db, model, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El registro ya existe o contiene datos inválidos.")

async def get_items(db: AsyncSession, model):
    return await MastersRepository.get_all_master(db, model)

async def get_item_by_id(db: AsyncSession, model, item_id: int):
    item = await MastersRepository.get_master_by_id(db, model, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado")
    return item

async def update_item(db: AsyncSession, model, item_id: int, data: dict):
    try:
        item = await MastersRepository.update_master(db, model, item_id, data)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado")
        return item
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo actualizar el registro por conflicto de datos.")

async def get_diagnoses_paginated(db: AsyncSession, skip: int, limit: int, code: Optional[str] = None, description: Optional[str] = None):
    return await MastersRepository.get_diagnoses_filtered(db, skip, limit, code, description)
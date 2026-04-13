from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.interfaces.infrastructure.repository import InterfacesRestRepository
from fastapi import HTTPException, status
from typing import Optional


# ========== INTERFACES REST ==========

async def create(db: AsyncSession, data: dict):
    """Create a new interface REST"""
    return await InterfacesRestRepository.create(db, data)

async def list_paginated(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    state: Optional[bool] = None,
    enterprise_id: Optional[int] = None
):
    """List interfaces REST with pagination"""
    items, total = await InterfacesRestRepository.get_paginated(db, skip, limit, search, state, enterprise_id)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_by_id(db: AsyncSession, interface_id: int):
    """Get interface REST by ID"""
    obj = await InterfacesRestRepository.get_by_id(db, interface_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interfaz REST con ID {interface_id} no encontrada"
        )
    return obj

async def update(db: AsyncSession, interface_id: int, update_data: dict):
    """Update an interface REST"""
    obj = await InterfacesRestRepository.update(db, interface_id, update_data)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interfaz REST con ID {interface_id} no encontrada"
        )
    return obj

async def delete(db: AsyncSession, interface_id: int):
    """Delete an interface REST"""
    return await InterfacesRestRepository.delete(db, interface_id)


# ========== INTERFACES REST DETAILS ==========

async def create_detail(db: AsyncSession, data: dict):
    """Create a new interface REST detail"""
    return await InterfacesRestRepository.create_detail(db, data)

async def list_details_paginated(
    db: AsyncSession,
    interface_id: int,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
):
    """List interface REST details with pagination"""
    obj = await InterfacesRestRepository.get_by_id(db, interface_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interfaz REST con ID {interface_id} no encontrada"
        )

    items, total = await InterfacesRestRepository.get_details_paginated(db, interface_id, skip, limit, search)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_detail_by_id(db: AsyncSession, detail_id: int):
    """Get interface REST detail by ID"""
    obj = await InterfacesRestRepository.get_detail_by_id(db, detail_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detalle de interfaz REST con ID {detail_id} no encontrado"
        )
    return obj

async def update_detail(db: AsyncSession, detail_id: int, update_data: dict):
    """Update an interface REST detail"""
    obj = await InterfacesRestRepository.update_detail(db, detail_id, update_data)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detalle de interfaz REST con ID {detail_id} no encontrado"
        )
    return obj

async def delete_detail(db: AsyncSession, detail_id: int):
    """Delete an interface REST detail"""
    return await InterfacesRestRepository.delete_detail(db, detail_id)

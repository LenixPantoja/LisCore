from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.locations.infrastructure.repository import LocationRepository
from fastapi import HTTPException, status
from typing import Optional

async def list_locations(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active: Optional[bool] = None
):
    """List locations with pagination"""
    items, total = await LocationRepository.get_paginated(db, skip, limit, search, active)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_location_by_id(db: AsyncSession, loc_id: int):
    """Get location by ID"""
    location = await LocationRepository.get_by_id(db, loc_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ubicación con ID {loc_id} no encontrada"
        )
    return location

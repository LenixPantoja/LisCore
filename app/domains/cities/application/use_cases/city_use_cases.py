from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.cities.infrastructure.repository import CityRepository
from fastapi import HTTPException, status
from typing import Optional

async def list_cities(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    department_id: Optional[int] = None
):
    """List cities with pagination"""
    items, total = await CityRepository.get_paginated(db, skip, limit, search, department_id)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_city_by_id(db: AsyncSession, city_id: int):
    """Get city by ID"""
    city = await CityRepository.get_by_id(db, city_id)
    if not city:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ciudad con ID {city_id} no encontrada"
        )
    return city

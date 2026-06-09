from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.cities.api.schemas import CityResponse, CityPaginatedResponse
from app.domains.cities.application.use_cases import city_use_cases as use_cases

router = APIRouter()

@router.get("/", response_model=CityPaginatedResponse,
            dependencies=[Depends(require_permission("Cities:List"))])
async def list_cities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List cities with pagination.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by city name or code (case-insensitive)
    - **department_id**: Filter by department ID
    """
    return await use_cases.list_cities(db, skip, limit, search, department_id)

@router.get("/{city_id}", response_model=CityResponse,
            dependencies=[Depends(require_permission("Cities:GetOne"))])
async def get_city(city_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a city by ID.
    """
    return await use_cases.get_city_by_id(db, city_id)

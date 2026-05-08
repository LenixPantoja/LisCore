from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.domains.locations.api.schemas import LocationResponse, LocationPaginatedResponse
from app.domains.locations.application.use_cases import location_use_cases as use_cases

router = APIRouter()

@router.get("/", response_model=LocationPaginatedResponse)
async def list_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List locations with pagination.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by location name (case-insensitive)
    - **active**: Filter by active status
    """
    return await use_cases.list_locations(db, skip, limit, search, active)

@router.get("/{loc_id}", response_model=LocationResponse)
async def get_location(loc_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a location by ID.
    """
    return await use_cases.get_location_by_id(db, loc_id)

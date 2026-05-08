from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.domains.Headquarters.api.schemas import HeadquarterCreate, HeadquarterUpdate, HeadquarterResponse, HeadquarterPaginatedResponse
from app.domains.Headquarters.application.use_cases import headquarter_use_cases

router = APIRouter()

@router.post("/", response_model=HeadquarterResponse, status_code=status.HTTP_201_CREATED)
async def create(data: HeadquarterCreate, db: AsyncSession = Depends(get_db)):
    return await headquarter_use_cases.create_hq(db, data.model_dump())

@router.get("/", response_model=HeadquarterPaginatedResponse)
async def list_headquarters(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List headquarters with pagination and optional filters.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by headquarter name (case-insensitive)
    - **active**: Filter by active status
    """
    return await headquarter_use_cases.list_hqs_paginated(db, skip, limit, search, active)

@router.get("/{hq_id}", response_model=HeadquarterResponse)
async def get_one(hq_id: int, db: AsyncSession = Depends(get_db)):
    return await headquarter_use_cases.get_hq_by_id(db, hq_id)

@router.patch("/{hq_id}", response_model=HeadquarterResponse)
async def update(hq_id: int, data: HeadquarterUpdate, db: AsyncSession = Depends(get_db)):
    return await headquarter_use_cases.update_hq(db, hq_id, data.model_dump(exclude_unset=True))

@router.delete("/{hq_id}")
async def delete(hq_id: int, db: AsyncSession = Depends(get_db)):
    return await headquarter_use_cases.delete_hq(db, hq_id)
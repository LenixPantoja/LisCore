from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.database import get_db
from app.domains.testslabs.api.schemas import TestsLabCreate, TestsLabUpdate, TestsLabResponse
from app.domains.studieslab.api.schemas import TestsLabPaginatedResponse
from app.domains.testslabs.application.use_cases import tests_lab_use_cases as use_cases

router = APIRouter()

@router.post("/", response_model=TestsLabResponse, status_code=status.HTTP_201_CREATED)
async def create(data: TestsLabCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_test(db, data.model_dump())

@router.get("/", response_model=TestsLabPaginatedResponse)
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await use_cases.list_tests(db, skip, limit, search)

@router.get("/{id}", response_model=TestsLabResponse)
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_test_by_id(db, id)

@router.patch("/{id}", response_model=TestsLabResponse)
async def update(id: int, data: TestsLabUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_test(db, id, data.model_dump(exclude_unset=True))

@router.delete("/{id}")
async def delete(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.delete_test(db, id)
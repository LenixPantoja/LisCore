from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.domains.Headquarters.api.schemas import HeadquarterCreate, HeadquarterUpdate, HeadquarterResponse
from app.domains.Headquarters.application.use_cases import headquarter_use_cases

router = APIRouter()

@router.post("/", response_model=HeadquarterResponse, status_code=status.HTTP_201_CREATED)
async def create(data: HeadquarterCreate, db: AsyncSession = Depends(get_db)):
    return await headquarter_use_cases.create_hq(db, data.model_dump())

@router.get("/", response_model=List[HeadquarterResponse])
async def list_all(db: AsyncSession = Depends(get_db)):
    return await headquarter_use_cases.list_hqs(db)

@router.get("/{hq_id}", response_model=HeadquarterResponse)
async def get_one(hq_id: int, db: AsyncSession = Depends(get_db)):
    return await headquarter_use_cases.get_hq_by_id(db, hq_id)

@router.patch("/{hq_id}", response_model=HeadquarterResponse)
async def update(hq_id: int, data: HeadquarterUpdate, db: AsyncSession = Depends(get_db)):
    return await headquarter_use_cases.update_hq(db, hq_id, data.model_dump(exclude_unset=True))

@router.delete("/{hq_id}")
async def delete(hq_id: int, db: AsyncSession = Depends(get_db)):
    return await headquarter_use_cases.delete_hq(db, hq_id)
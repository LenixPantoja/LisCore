from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.domains.samples.api.schemas import SampleTypeCreate, SampleTypeUpdate, SampleTypeResponse
from app.domains.samples.application.use_cases import sample_types_use_cases as use_cases

router = APIRouter()

@router.get("/types", response_model=List[SampleTypeResponse])
async def list_types(db: AsyncSession = Depends(get_db)):
    return await use_cases.list_sample_types(db)

@router.get("/types/{st_id}", response_model=SampleTypeResponse)
async def get_one_type(st_id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_sample_type_by_id(db, st_id)

@router.post("/types", response_model=SampleTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_type(data: SampleTypeCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_sample_type(db, data.model_dump())

@router.patch("/types/{st_id}", response_model=SampleTypeResponse)
async def update_type(st_id: int, data: SampleTypeUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_sample_type(db, st_id, data.model_dump(exclude_unset=True))

@router.delete("/types/{st_id}")
async def delete_type(st_id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.delete_sample_type(db, st_id)
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.samples.api.schemas import SampleTypeCreate, SampleTypeUpdate, SampleTypeResponse, SampleTypePaginatedResponse
from app.domains.samples.application.use_cases import sample_types_use_cases as use_cases, list_sample_types

router = APIRouter()

@router.get("/types", response_model=SampleTypePaginatedResponse,
            dependencies=[Depends(require_permission("Samples:List"))])
async def list_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await list_sample_types.execute(db, skip, limit, search)

@router.get("/types/{st_id}", response_model=SampleTypeResponse,
            dependencies=[Depends(require_permission("Samples:GetOne"))])
async def get_one_type(st_id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_sample_type_by_id(db, st_id)

@router.post("/types", response_model=SampleTypeResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("Samples:Create"))])
async def create_type(data: SampleTypeCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_sample_type(db, data.model_dump())

@router.patch("/types/{st_id}", response_model=SampleTypeResponse,
              dependencies=[Depends(require_permission("Samples:Update"))])
async def update_type(st_id: int, data: SampleTypeUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_sample_type(db, st_id, data.model_dump(exclude_unset=True))

@router.delete("/types/{st_id}",
               dependencies=[Depends(require_permission("Samples:Delete"))])
async def delete_type(st_id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.delete_sample_type(db, st_id)
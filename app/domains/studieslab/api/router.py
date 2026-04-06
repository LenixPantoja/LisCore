from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.domains.studieslab.api.schemas import (
    StudiesLabCreate, StudiesLabUpdate, StudiesLabResponse, 
    StudiesTestDetailCreate, StudiesTestDetailResponse
)
from app.domains.studieslab.infrastructure.repository import StudiesLabRepository

router = APIRouter()

@router.post("/", response_model=StudiesLabResponse, status_code=status.HTTP_201_CREATED)
async def create_study(data: StudiesLabCreate, db: AsyncSession = Depends(get_db)):
    return await StudiesLabRepository.create(db, data.model_dump())

@router.get("/", response_model=List[StudiesLabResponse])
async def list_studies(db: AsyncSession = Depends(get_db)):
    return await StudiesLabRepository.get_all(db)

@router.get("/{id}", response_model=StudiesLabResponse)
async def get_study(id: int, db: AsyncSession = Depends(get_db)):
    study = await StudiesLabRepository.get_by_id(db, id)
    if not study:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    return study

@router.patch("/{id}", response_model=StudiesLabResponse)
async def update_study(id: int, data: StudiesLabUpdate, db: AsyncSession = Depends(get_db)):
    study = await StudiesLabRepository.update(db, id, data.model_dump(exclude_unset=True))
    if not study:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    return study

# --- Endpoints para Detalle ---
@router.post("/{study_id}/tests", response_model=StudiesTestDetailResponse)
async def add_test_to_study(study_id: int, data: StudiesTestDetailCreate, db: AsyncSession = Depends(get_db)):
    return await StudiesLabRepository.add_test_detail(db, study_id, data.model_dump())

@router.delete("/tests-detail/{detail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_test_from_study(detail_id: int, db: AsyncSession = Depends(get_db)):
    if not await StudiesLabRepository.remove_test_detail(db, detail_id):
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
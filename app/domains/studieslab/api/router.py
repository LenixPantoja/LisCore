from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.domains.studieslab.api.schemas import (
    StudiesLabCreate, StudiesLabUpdate, StudiesLabResponse, StudiesLabPaginatedResponse,
    StudiesTestDetailCreate, StudiesTestDetailResponse
)
from app.domains.studieslab.infrastructure.repository import StudiesLabRepository

router = APIRouter()

@router.post("/", response_model=StudiesLabResponse, status_code=status.HTTP_201_CREATED)
async def create_study(data: StudiesLabCreate, db: AsyncSession = Depends(get_db)):
    new_study = await StudiesLabRepository.create(db, data.model_dump())
    # Fetch the newly created study with all its relationships for proper response serialization
    return await StudiesLabRepository.get_by_id(db, new_study.id)

@router.get("/", response_model=StudiesLabPaginatedResponse)
async def list_studies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    items, total = await StudiesLabRepository.get_paginated(db, skip, limit, search)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

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
    # Volvemos a consultar el estudio con sus relaciones cargadas para evitar errores de serialización
    return await StudiesLabRepository.get_by_id(db, id)

# --- Endpoints para Detalle ---
@router.post("/{study_id}/tests", response_model=StudiesTestDetailResponse)
async def add_test_to_study(study_id: int, data: StudiesTestDetailCreate, db: AsyncSession = Depends(get_db)):
    # Create the detail and then fetch it with relationships for proper response serialization
    new_detail = await StudiesLabRepository.add_test_detail(db, study_id, data.model_dump())
    
    # Ensure relationships are loaded for the response model
    from sqlalchemy.future import select
    from sqlalchemy.orm import selectinload
    from app.domains.studieslab.domain.models import StudiesTestDetail # Import if not already

    loaded_detail_query = await db.execute(
        select(StudiesTestDetail).filter(StudiesTestDetail.id == new_detail.id)
        .options(selectinload(StudiesTestDetail.test), selectinload(StudiesTestDetail.work_group))
    )
    return loaded_detail_query.scalars().first()

@router.delete("/tests-detail/{detail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_test_from_study(detail_id: int, db: AsyncSession = Depends(get_db)):
    if not await StudiesLabRepository.remove_test_detail(db, detail_id):
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
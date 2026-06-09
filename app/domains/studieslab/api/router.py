from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.studieslab.api.schemas import (
    StudiesLabCreate, StudiesLabUpdate, StudiesLabResponse, StudiesLabPaginatedResponse,
    StudiesTestDetailCreate, StudiesTestDetailUpdate, StudiesTestDetailResponse
)
from app.domains.studieslab.infrastructure.repository import StudiesLabRepository
from app.domains.studieslab.application.use_cases import studies_use_cases as use_cases

router = APIRouter()

@router.post("/", response_model=StudiesLabResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("StudiesLab:Create"))])
async def create_study(data: StudiesLabCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_study(db, data.model_dump())

@router.get("/", response_model=StudiesLabPaginatedResponse,
            dependencies=[Depends(require_permission("StudiesLab:List"))])
async def list_studies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await use_cases.list_studies(db, skip, limit, search)

@router.get("/{id}", response_model=StudiesLabResponse,
            dependencies=[Depends(require_permission("StudiesLab:GetOne"))])
async def get_study(id: int, db: AsyncSession = Depends(get_db)):
    study = await StudiesLabRepository.get_by_id(db, id)
    if not study:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    return study

@router.patch("/{id}", response_model=StudiesLabResponse,
              dependencies=[Depends(require_permission("StudiesLab:Update"))])
async def update_study(id: int, data: StudiesLabUpdate, db: AsyncSession = Depends(get_db)):
    study = await StudiesLabRepository.update(db, id, data.model_dump(exclude_unset=True))
    if not study:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    # Volvemos a consultar el estudio con sus relaciones cargadas para evitar errores de serialización
    return await StudiesLabRepository.get_by_id(db, id)

# --- Endpoints para Detalle ---
@router.post("/{study_id}/tests", response_model=StudiesTestDetailResponse,
             dependencies=[Depends(require_permission("StudiesLab:ManageTests"))])
async def add_test_to_study(study_id: int, data: StudiesTestDetailCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.add_test_to_study(db, study_id, data.model_dump())

@router.patch("/tests-detail/{detail_id}", response_model=StudiesTestDetailResponse,
              dependencies=[Depends(require_permission("StudiesLab:ManageTests"))])
async def update_test_from_study(detail_id: int, data: StudiesTestDetailUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_test_detail(db, detail_id, data.model_dump(exclude_unset=True))

@router.delete("/tests-detail/{detail_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("StudiesLab:ManageTests"))])
async def remove_test_from_study(detail_id: int, db: AsyncSession = Depends(get_db)):
    if not await StudiesLabRepository.remove_test_detail(db, detail_id):
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
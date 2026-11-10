from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.medics.api.schemas import (
    MedicCreate,
    MedicOption,
    MedicPaginatedResponse,
    MedicResponse,
    MedicUpdate,
)
from app.domains.medics.application.use_cases import medic_use_cases as use_cases

router = APIRouter(redirect_slashes=False)


@router.get(
    "",
    response_model=MedicPaginatedResponse,
    dependencies=[Depends(require_permission("Medics:List"))],
)
async def list_medics(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None, max_length=100, description="Texto libre: código exacto, o parte del nombre, documento, especialidad, tarjeta profesional o usuario"),
    codigo: Optional[str] = Query(None, max_length=30, description="Código del médico (exacto)"),
    name: Optional[str] = Query(None, max_length=200, description="Nombre del médico (coincidencia parcial)"),
    is_active: Optional[bool] = Query(None, description="Filtra por activos (true) o inactivos (false)"),
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.list_medics(db, skip, limit, search, is_active, codigo, name)


@router.get(
    "/active",
    response_model=List[MedicOption],
    dependencies=[Depends(require_permission("Medics:List"))],
)
async def list_active_medics(
    search: Optional[str] = Query(None, max_length=100, description="Texto libre: código exacto, o parte del nombre, documento o especialidad"),
    codigo: Optional[str] = Query(None, max_length=30, description="Código del médico (exacto)"),
    name: Optional[str] = Query(None, max_length=200, description="Nombre del médico (coincidencia parcial)"),
    db: AsyncSession = Depends(get_db),
):
    """Médicos activos y no bloqueados, para elegir el médico al crear una orden."""
    return await use_cases.list_active_medics(db, search, codigo, name)


@router.get(
    "/{med_id}",
    response_model=MedicResponse,
    dependencies=[Depends(require_permission("Medics:GetOne"))],
)
async def get_medic(med_id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_medic(db, med_id)


@router.post(
    "",
    response_model=MedicResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("Medics:Create"))],
)
async def create_medic(body: MedicCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_medic(db, body.model_dump())


@router.put(
    "/{med_id}",
    response_model=MedicResponse,
    dependencies=[Depends(require_permission("Medics:Update"))],
)
async def update_medic(med_id: int, body: MedicUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_medic(db, med_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/{med_id}",
    dependencies=[Depends(require_permission("Medics:Delete"))],
)
async def delete_medic(med_id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.delete_medic(db, med_id)

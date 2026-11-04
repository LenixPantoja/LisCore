from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.worksheets.api.schemas import (
    WorkSheetCreate,
    WorkSheetDetailResponse,
    WorkSheetPaginatedResponse,
    WorkSheetStudiesUpdate,
    WorkSheetUpdate,
)
from app.domains.worksheets.application.use_cases import worksheet_use_cases as use_cases

router = APIRouter(redirect_slashes=False)


@router.get(
    "",
    response_model=WorkSheetPaginatedResponse,
    dependencies=[Depends(require_permission("WorkSheets:List"))],
)
async def list_worksheets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, max_length=100),
    active_only: bool = Query(False),
    work_group_id: Optional[int] = Query(None),
    headquarter_id: Optional[int] = Query(None, description="Incluye también las hojas de todas las sedes"),
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.list_worksheets(db, skip, limit, search, active_only, work_group_id, headquarter_id)


@router.get(
    "/{ws_id}",
    response_model=WorkSheetDetailResponse,
    dependencies=[Depends(require_permission("WorkSheets:List"))],
)
async def get_worksheet(ws_id: int, db: AsyncSession = Depends(get_db)):
    """Hoja de trabajo con sus estudios en el orden de impresión."""
    return await use_cases.get_worksheet(db, ws_id)


@router.post(
    "",
    response_model=WorkSheetDetailResponse,
    dependencies=[Depends(require_permission("WorkSheets:Manage"))],
)
async def create_worksheet(body: WorkSheetCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_worksheet(db, body.model_dump())


@router.put(
    "/{ws_id}",
    response_model=WorkSheetDetailResponse,
    dependencies=[Depends(require_permission("WorkSheets:Manage"))],
)
async def update_worksheet(ws_id: int, body: WorkSheetUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_worksheet(db, ws_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/{ws_id}",
    dependencies=[Depends(require_permission("WorkSheets:Manage"))],
)
async def delete_worksheet(ws_id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.delete_worksheet(db, ws_id)


@router.put(
    "/{ws_id}/studies",
    response_model=WorkSheetDetailResponse,
    dependencies=[Depends(require_permission("WorkSheets:Manage"))],
)
async def set_worksheet_studies(ws_id: int, body: WorkSheetStudiesUpdate, db: AsyncSession = Depends(get_db)):
    """Reemplaza los estudios de la hoja; el orden de la lista es el orden de impresión."""
    return await use_cases.set_worksheet_studies(db, ws_id, body.study_ids)

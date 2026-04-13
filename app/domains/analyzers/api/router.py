from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.domains.analyzers.api.schemas import (
    AnalyzerGroupCreate,
    AnalyzerGroupUpdate,
    AnalyzerGroupResponse,
    AnalyzerGroupPaginatedResponse,
    AnalyzerCreate,
    AnalyzerUpdate,
    AnalyzerResponse,
    AnalyzerPaginatedResponse,
    AnalyzerDetailCreate,
    AnalyzerDetailUpdate,
    AnalyzerDetailResponse,
    AnalyzerDetailPaginatedResponse,
)
from app.domains.analyzers.application.use_cases import analyzer_use_cases

router = APIRouter()

# ========== ANALYZER GROUPS ==========

@router.post("/analyzer-groups", response_model=AnalyzerGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_analyzer_group(data: AnalyzerGroupCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new analyzer group.

    - **ag_name**: Group name (optional)
    - **ag_active**: Whether the group is active (default: True)
    """
    return await analyzer_use_cases.create_analyzer_group(db, data.model_dump())

@router.get("/analyzer-groups", response_model=AnalyzerGroupPaginatedResponse)
async def list_analyzer_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List analyzer groups with pagination.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by group name (case-insensitive)
    - **active**: Filter by active status
    """
    return await analyzer_use_cases.list_analyzer_groups(db, skip, limit, search, active)

@router.get("/analyzer-groups/{group_id}", response_model=AnalyzerGroupResponse)
async def get_analyzer_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get an analyzer group by ID.
    """
    return await analyzer_use_cases.get_analyzer_group_by_id(db, group_id)

@router.patch("/analyzer-groups/{group_id}", response_model=AnalyzerGroupResponse)
async def update_analyzer_group(group_id: int, data: AnalyzerGroupUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an analyzer group.

    Only sends the fields you want to update.
    """
    return await analyzer_use_cases.update_analyzer_group(db, group_id, data.model_dump(exclude_unset=True))

@router.delete("/analyzer-groups/{group_id}", status_code=status.HTTP_200_OK)
async def delete_analyzer_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete an analyzer group.
    """
    return await analyzer_use_cases.delete_analyzer_group(db, group_id)


# ========== ANALYZERS ==========

@router.post("/analyzers", response_model=AnalyzerResponse, status_code=status.HTTP_201_CREATED)
async def create_analyzer(data: AnalyzerCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new analyzer.

    - **a_name**: Analyzer name (optional)
    - **a_description**: Description (optional)
    - **a_analyzer_group_id**: Analyzer group ID (FK, optional)
    - **a_work_group_id**: Work group ID (FK, optional)
    - **a_licence**: License text (optional)
    - **a_active**: Whether active (default: True)
    """
    return await analyzer_use_cases.create_analyzer(db, data.model_dump())

@router.get("/analyzers", response_model=AnalyzerPaginatedResponse)
async def list_analyzers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    group_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List analyzers with pagination.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by analyzer name (case-insensitive)
    - **active**: Filter by active status
    - **group_id**: Filter by analyzer group ID
    """
    return await analyzer_use_cases.list_analyzers(db, skip, limit, search, active, group_id)

@router.get("/analyzers/{analyzer_id}", response_model=AnalyzerResponse)
async def get_analyzer(analyzer_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get an analyzer by ID with its group, work group, and details.
    """
    return await analyzer_use_cases.get_analyzer_by_id(db, analyzer_id)

@router.patch("/analyzers/{analyzer_id}", response_model=AnalyzerResponse)
async def update_analyzer(analyzer_id: int, data: AnalyzerUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an analyzer.

    Only sends the fields you want to update. Auto-updates `a_updated_at`.
    """
    return await analyzer_use_cases.update_analyzer(db, analyzer_id, data.model_dump(exclude_unset=True))

@router.delete("/analyzers/{analyzer_id}", status_code=status.HTTP_200_OK)
async def delete_analyzer(analyzer_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete an analyzer.
    """
    return await analyzer_use_cases.delete_analyzer(db, analyzer_id)


# ========== ANALYZER DETAILS ==========

@router.post("/analyzers/{analyzer_id}/details", response_model=AnalyzerDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_analyzer_detail(analyzer_id: int, data: AnalyzerDetailCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new analyzer detail.

    - **ad_analyzer_id**: Analyzer ID (required)
    - **ad_transmission_code**: Transmission code (optional)
    - **ad_receipt_code_results**: Receipt code results (optional)
    - **ad_test_id**: Test ID (FK, optional)
    - **ad_sufix**: Suffix (optional)
    - **ad_active**: Whether active (default: True)
    """
    payload = data.model_dump()
    payload['ad_analyzer_id'] = analyzer_id
    return await analyzer_use_cases.create_analyzer_detail(db, payload)

@router.get("/analyzers/{analyzer_id}/details", response_model=AnalyzerDetailPaginatedResponse)
async def list_analyzer_details(
    analyzer_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List analyzer details with pagination.

    - **analyzer_id**: Analyzer ID (path parameter)
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by transmission code or suffix (case-insensitive)
    - **active**: Filter by active status
    """
    return await analyzer_use_cases.list_analyzer_details(db, analyzer_id, skip, limit, search, active)

@router.get("/analyzers/details/{detail_id}", response_model=AnalyzerDetailResponse)
async def get_analyzer_detail(detail_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get an analyzer detail by ID with its linked test information.
    """
    return await analyzer_use_cases.get_analyzer_detail_by_id(db, detail_id)

@router.patch("/analyzers/details/{detail_id}", response_model=AnalyzerDetailResponse)
async def update_analyzer_detail(detail_id: int, data: AnalyzerDetailUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an analyzer detail.

    Only sends the fields you want to update. Auto-updates `ad_updated_at`.
    """
    return await analyzer_use_cases.update_analyzer_detail(db, detail_id, data.model_dump(exclude_unset=True))

@router.delete("/analyzers/details/{detail_id}", status_code=status.HTTP_200_OK)
async def delete_analyzer_detail(detail_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete (unlink) an analyzer detail.
    """
    return await analyzer_use_cases.delete_analyzer_detail(db, detail_id)

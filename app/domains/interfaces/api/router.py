from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.domains.interfaces.api.schemas import (
    InterfacesRestCreate,
    InterfacesRestUpdate,
    InterfacesRestResponse,
    InterfacesRestPaginatedResponse,
    InterfacesRestDetailCreate,
    InterfacesRestDetailUpdate,
    InterfacesRestDetailResponse,
    InterfacesRestDetailPaginatedResponse,
)
from app.domains.interfaces.application.use_cases import interfaces_rest_use_cases as use_cases

router = APIRouter()

# ========== INTERFACES REST ==========

@router.post("/interfaces-rest", response_model=InterfacesRestResponse, status_code=status.HTTP_201_CREATED)
async def create_interface(data: InterfacesRestCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new interface REST.

    - **it_enterprise_id**: Enterprise ID (FK, optional)
    - **it_tariff_id**: Tariff ID (FK, optional)
    - **it_state**: Whether the interface is active (default: True)
    """
    return await use_cases.create(db, data.model_dump())

@router.get("/interfaces-rest", response_model=InterfacesRestPaginatedResponse)
async def list_interfaces(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(
        None,
        description="Buscar por nombre de empresa o NIT",
    ),
    state: Optional[bool] = None,
    enterprise_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List interfaces REST with pagination.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by enterprise name or NIT
    - **state**: Filter by active status
    - **enterprise_id**: Filter by enterprise ID
    """
    return await use_cases.list_paginated(db, skip, limit, search=search, state=state, enterprise_id=enterprise_id)

@router.get("/interfaces-rest/{interface_id}", response_model=InterfacesRestResponse)
async def get_interface(interface_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get an interface REST by ID with its enterprise, tariff, and details.
    """
    return await use_cases.get_by_id(db, interface_id)

@router.patch("/interfaces-rest/{interface_id}", response_model=InterfacesRestResponse)
async def update_interface(interface_id: int, data: InterfacesRestUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an interface REST.

    Only sends the fields you want to update. Auto-updates `it_updated_at`.
    """
    return await use_cases.update(db, interface_id, data.model_dump(exclude_unset=True))

@router.delete("/interfaces-rest/{interface_id}", status_code=status.HTTP_200_OK)
async def delete_interface(interface_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete an interface REST.
    """
    return await use_cases.delete(db, interface_id)


# ========== INTERFACES REST DETAILS ==========

@router.post("/interfaces-rest/{interface_id}/details", response_model=InterfacesRestDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_interface_detail(interface_id: int, data: InterfacesRestDetailCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new interface REST detail.

    - **itd_interface_rest_id**: Interface ID (required, auto-set from path)
    - **itd_study_id**: Study ID (FK, optional)
    - **itd_send_code**: Send code (optional)
    - **itd_receipt_code**: Receipt code (optional)
    """
    payload = data.model_dump()
    payload['itd_interface_rest_id'] = interface_id
    return await use_cases.create_detail(db, payload)

@router.get("/interfaces-rest/{interface_id}/details", response_model=InterfacesRestDetailPaginatedResponse)
async def list_interface_details(
    interface_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List interface REST details with pagination.

    - **interface_id**: Interface ID (path parameter)
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by send code or receipt code (case-insensitive)
    """
    return await use_cases.list_details_paginated(db, interface_id, skip, limit, search)

@router.get("/interfaces-rest/details/{detail_id}", response_model=InterfacesRestDetailResponse)
async def get_interface_detail(detail_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get an interface REST detail by ID with its linked study information.
    """
    return await use_cases.get_detail_by_id(db, detail_id)

@router.patch("/interfaces-rest/details/{detail_id}", response_model=InterfacesRestDetailResponse)
async def update_interface_detail(detail_id: int, data: InterfacesRestDetailUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an interface REST detail.

    Only sends the fields you want to update. Auto-updates `itd_updated_at`.
    """
    return await use_cases.update_detail(db, detail_id, data.model_dump(exclude_unset=True))

@router.delete("/interfaces-rest/details/{detail_id}", status_code=status.HTTP_200_OK)
async def delete_interface_detail(detail_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete (unlink) an interface REST detail.
    """
    return await use_cases.delete_detail(db, detail_id)

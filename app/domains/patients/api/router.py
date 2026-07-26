from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import require_permission, get_current_user
from app.domains.users.infrastructure.models import AppUser
from app.domains.patients.api.schemas import PatientCreate, PatientUpdate, PatientResponse, PatientWithAgeResponse, PatientPaginatedResponse
from app.domains.orders.api.schemas import PatientOrdersPaginatedResponse
from app.domains.patients.application.use_cases import patient_use_cases as use_cases

router = APIRouter()

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("Patients:Create"))])
async def create(
    data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await use_cases.create_patient(db, data.model_dump(), current_user.usr_id)

@router.get("/", response_model=PatientPaginatedResponse,
            dependencies=[Depends(require_permission("Patients:List"))])
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Listar pacientes con paginación y búsqueda opcional.
    """
    return await use_cases.list_patients(db, skip, limit, search)

@router.get("/document/{doc_number}", response_model=PatientWithAgeResponse,
            dependencies=[Depends(require_permission("Patients:GetOne"))])
async def get_by_document(doc_number: str, db: AsyncSession = Depends(get_db)):
    """
    Get a patient by document number with calculated age.
    """
    patient = await use_cases.get_patient_by_document(db, doc_number)
    return patient

@router.get("/document/{search_query}/orders", response_model=PatientOrdersPaginatedResponse,
            dependencies=[Depends(require_permission("Patients:GetOne"))])
async def get_orders_by_document_or_order_number(
    search_query: str, 
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated orders matching the search_query either by patient document number OR order number.
    """
    return await use_cases.get_patient_orders_with_details(db, search_query, skip, limit)

@router.get("/{id}", response_model=PatientResponse,
            dependencies=[Depends(require_permission("Patients:GetOne"))])
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_patient_by_id(db, id)

@router.patch("/{id}", response_model=PatientResponse,
              dependencies=[Depends(require_permission("Patients:Update"))])
async def update(
    id: int,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await use_cases.update_patient(
        db, id, data.model_dump(exclude_unset=True), user_id=current_user.usr_id
    )

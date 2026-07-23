from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.app_results_page.api.dependencies import (
    get_current_portal_enterprise,
    get_current_portal_patient,
    get_current_portal_user,
)
from app.domains.app_results_page.api.schemas import (
    EnterpriseOrdersPaginatedResponse,
    MessageResponse,
    PatientOrdersPaginatedResponse,
    PortalChangePasswordRequest,
    PortalLoginRequest,
    PortalLoginResponse,
)
from app.domains.app_results_page.application.use_cases import auth_use_cases, results_use_cases
from app.domains.app_results_page.domain.models import AppResultsPage
from app.domains.enterprises.domain.models import Enterprise
from app.domains.patients.domain.models import Patient

router = APIRouter(prefix="/app-results-page", tags=["App Results Page"])


@router.post("/login", response_model=PortalLoginResponse)
async def login(data: PortalLoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_use_cases.login(db, data.login, data.password)


@router.patch("/change-password", response_model=MessageResponse)
async def change_password(
    data: PortalChangePasswordRequest,
    arp_user: AppResultsPage = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_db),
):
    await auth_use_cases.change_password(db, arp_user, data.current_password, data.new_password)
    return {"detail": "Contraseña actualizada correctamente."}


@router.get("/patient/orders", response_model=PatientOrdersPaginatedResponse)
async def list_patient_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    patient: Patient = Depends(get_current_portal_patient),
    db: AsyncSession = Depends(get_db),
):
    return await results_use_cases.list_patient_orders(db, patient, page, page_size, search)


@router.get("/enterprise/orders", response_model=EnterpriseOrdersPaginatedResponse)
async def list_enterprise_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    enterprise: Enterprise = Depends(get_current_portal_enterprise),
    db: AsyncSession = Depends(get_db),
):
    return await results_use_cases.list_enterprise_orders(db, enterprise, page, page_size, search)

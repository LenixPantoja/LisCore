from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.app_results_page.api.dependencies import (
    get_current_portal_enterprise,
    get_current_portal_patient,
    get_current_portal_user,
)
from app.domains.app_results_page.api.schemas import (
    EnterpriseOrdersPaginatedResponse,
    EvolutionResponse,
    MessageResponse,
    PatientOrdersPaginatedResponse,
    PortalChangePasswordRequest,
    PortalLoginRequest,
    PortalLoginResponse,
)
from app.domains.app_results_page.application.use_cases import (
    auth_use_cases,
    evolution_use_cases,
    results_use_cases,
)
from app.domains.app_results_page.domain.models import AppResultsPage
from app.domains.enterprises.domain.models import Enterprise
from app.domains.patients.domain.models import Patient

router = APIRouter(prefix="/app-results-page", tags=["App Results Page"])

# Logo del portal en memoria: evita ir a MinIO en cada visita al login
_LOGO_CACHE: dict = {"data": None, "mime": None, "at": 0.0}
_LOGO_TTL_SECONDS = 300


@router.get("/branding/logo", include_in_schema=True, summary="Logo del laboratorio para el portal")
async def get_portal_logo():
    """
    Logo del laboratorio (bucket de recursos de MinIO, objeto PORTAL_LOGO_OBJECT).
    Público: lo usa la pantalla de inicio de sesión. Para cambiarlo basta con
    reemplazar el archivo en MinIO; se refresca en máximo 5 minutos.
    """
    import asyncio
    import time
    from fastapi import HTTPException, Response
    from app.core.config import settings
    from utils.minio_client import download_resource

    now = time.monotonic()
    if not _LOGO_CACHE["data"] or now - _LOGO_CACHE["at"] > _LOGO_TTL_SECONDS:
        name = settings.PORTAL_LOGO_OBJECT
        data = await asyncio.to_thread(download_resource, name)
        if data:
            low = name.lower()
            mime = ("image/jpeg" if low.endswith((".jpg", ".jpeg")) else
                    "image/svg+xml" if low.endswith(".svg") else
                    "image/webp" if low.endswith(".webp") else "image/png")
            _LOGO_CACHE.update(data=data, mime=mime, at=now)
        elif not _LOGO_CACHE["data"]:
            raise HTTPException(status_code=404, detail="Logo no disponible.")
    return Response(
        content=_LOGO_CACHE["data"],
        media_type=_LOGO_CACHE["mime"],
        headers={"Cache-Control": "public, max-age=300"},
    )


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


@router.get("/patient/evolution/{test_id}", response_model=EvolutionResponse)
async def get_patient_evolution(
    test_id: int = Path(..., ge=1),
    patient: Patient = Depends(get_current_portal_patient),
    db: AsyncSession = Depends(get_db),
):
    """Gráfico evolutivo de un examen para el paciente autenticado (con valores de referencia)."""
    return await evolution_use_cases.get_patient_evolution(db, patient, test_id)


@router.get("/enterprise/evolution/{test_id}", response_model=EvolutionResponse)
async def get_enterprise_patient_evolution(
    test_id: int = Path(..., ge=1),
    document_number: str = Query(..., min_length=1),
    enterprise: Enterprise = Depends(get_current_portal_enterprise),
    db: AsyncSession = Depends(get_db),
):
    """Gráfico evolutivo de un examen para un paciente de la empresa (sólo órdenes de la empresa)."""
    return await evolution_use_cases.get_enterprise_patient_evolution(db, enterprise, document_number, test_id)

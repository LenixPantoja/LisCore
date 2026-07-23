from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.domains.app_results_page.domain.constants import ACCESS_TYPE_ENTERPRISE, ACCESS_TYPE_PATIENT
from app.domains.app_results_page.domain.models import AppResultsPage
from app.domains.app_results_page.infrastructure.repository import AppResultsPageRepository
from app.domains.enterprises.domain.models import Enterprise
from app.domains.enterprises.infrastructure.repository import EnterpriseRepository
from app.domains.patients.domain.models import Patient
from app.domains.patients.infrastructure.repository import PatientRepository

_bearer = HTTPBearer()


async def get_current_portal_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> AppResultsPage:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access" or not payload.get("portal"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        arp_user_id: Optional[int] = payload.get("id")
        if arp_user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    arp_user = await AppResultsPageRepository.get_by_id(db, arp_user_id)
    if arp_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not arp_user.arp_user_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    return arp_user


async def get_current_portal_patient(
    arp_user: AppResultsPage = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_db),
) -> Patient:
    if arp_user.arp_user_access_type != ACCESS_TYPE_PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este recurso es solo para pacientes.")
    patient = await PatientRepository.get_by_id(db, arp_user.arp_user_origin_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Paciente no encontrado")
    return patient


async def get_current_portal_enterprise(
    arp_user: AppResultsPage = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_db),
) -> Enterprise:
    if arp_user.arp_user_access_type != ACCESS_TYPE_ENTERPRISE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este recurso es solo para empresas.")
    enterprise = await EnterpriseRepository.get_by_id(db, arp_user.arp_user_origin_id)
    if enterprise is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empresa no encontrada")
    return enterprise

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.domains.app_results_page.domain.constants import ACCESS_TYPE_ENTERPRISE, ACCESS_TYPE_PATIENT
from app.domains.app_results_page.domain.helpers import full_name, resolve_sex
from app.domains.app_results_page.domain.models import AppResultsPage
from app.domains.app_results_page.infrastructure.repository import AppResultsPageRepository
from app.domains.enterprises.infrastructure.repository import EnterpriseRepository
from app.domains.patients.infrastructure.repository import PatientRepository

_INVALID_CREDENTIALS = "Usuario o contraseña incorrectos."
_MIN_PASSWORD_LENGTH = 6


async def login(db: AsyncSession, login_value: str, password: str) -> dict:
    arp_user = await AppResultsPageRepository.get_by_login(db, login_value)
    if not arp_user or not arp_user.arp_user_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)

    if arp_user.arp_user_access_type == ACCESS_TYPE_PATIENT:
        patient = await PatientRepository.get_by_id(db, arp_user.arp_user_origin_id)
        if not patient or not patient.pt_password or not verify_password(password, patient.pt_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)
        response_data = {
            "patient": {
                "pt_id": patient.pt_id,
                "document_number": patient.pt_Number_document,
                "fullname": full_name(patient),
                "mail": patient.pt_mail,
                "phone_number": patient.pt_phone_number,
                "date_of_birth": patient.pt_date_of_birth,
                "sex": resolve_sex(patient),
            },
            "enterprise": None,
        }
    elif arp_user.arp_user_access_type == ACCESS_TYPE_ENTERPRISE:
        enterprise = await EnterpriseRepository.get_by_id(db, arp_user.arp_user_origin_id)
        if not enterprise or not enterprise.en_password or not verify_password(password, enterprise.en_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)
        response_data = {
            "patient": None,
            "enterprise": {
                "en_id": enterprise.en_id,
                "nit": enterprise.en_nit,
                "name": enterprise.en_name,
                "mail": enterprise.en_mail,
            },
        }
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de acceso no soportado.")

    await AppResultsPageRepository.touch_last_access(db, arp_user)

    token_payload = {
        "sub": arp_user.arp_user_login,
        "id": arp_user.arp_user_id,
        "access_type": arp_user.arp_user_access_type,
        "portal": True,
    }
    access_token = create_access_token(
        data=token_payload,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "arp_user_access_type": arp_user.arp_user_access_type,
        **response_data,
    }


async def change_password(
    db: AsyncSession,
    arp_user: AppResultsPage,
    current_password: str,
    new_password: str,
) -> None:
    if len(new_password) < _MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La nueva contraseña debe tener al menos {_MIN_PASSWORD_LENGTH} caracteres.",
        )

    if arp_user.arp_user_access_type == ACCESS_TYPE_PATIENT:
        patient = await PatientRepository.get_by_id(db, arp_user.arp_user_origin_id)
        if not patient or not patient.pt_password or not verify_password(current_password, patient.pt_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La contraseña actual no es correcta.")
        await PatientRepository.update(db, patient.pt_id, {"pt_password": get_password_hash(new_password)})

    elif arp_user.arp_user_access_type == ACCESS_TYPE_ENTERPRISE:
        enterprise = await EnterpriseRepository.get_by_id(db, arp_user.arp_user_origin_id)
        if not enterprise or not enterprise.en_password or not verify_password(current_password, enterprise.en_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La contraseña actual no es correcta.")
        await EnterpriseRepository.update(db, enterprise, {"en_password": get_password_hash(new_password)})

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de acceso no soportado.")

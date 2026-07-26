import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.app_results_page.domain.constants import ACCESS_TYPE_ENTERPRISE, ACCESS_TYPE_PATIENT
from app.domains.app_results_page.domain.models import AppResultsPage
from app.domains.app_results_page.infrastructure.repository import AppResultsPageRepository

logger = logging.getLogger(__name__)


async def provision_for_patient(db: AsyncSession, patient) -> AppResultsPage | None:
    """Crea el usuario del portal de resultados para un paciente recién creado (idempotente)."""
    existing = await AppResultsPageRepository.get_by_origin(db, patient.pt_id, ACCESS_TYPE_PATIENT)
    if existing:
        return existing
    try:
        return await AppResultsPageRepository.create(db, {
            "arp_user_origin_id": patient.pt_id,
            "arp_user_login": patient.pt_Number_document,
            "arp_user_mail": patient.pt_mail,
            "arp_user_access_type": ACCESS_TYPE_PATIENT,
        })
    except IntegrityError:
        await db.rollback()
        logger.warning(
            "No se pudo crear el usuario del portal de resultados para el paciente %s (login duplicado: %s)",
            patient.pt_id, patient.pt_Number_document,
        )
        return None


async def provision_for_enterprise(db: AsyncSession, enterprise) -> AppResultsPage | None:
    """Crea el usuario del portal de resultados para una empresa recién creada (idempotente)."""
    existing = await AppResultsPageRepository.get_by_origin(db, enterprise.en_id, ACCESS_TYPE_ENTERPRISE)
    if existing:
        return existing
    try:
        return await AppResultsPageRepository.create(db, {
            "arp_user_origin_id": enterprise.en_id,
            "arp_user_login": enterprise.en_nit,
            "arp_user_mail": enterprise.en_mail,
            "arp_user_access_type": ACCESS_TYPE_ENTERPRISE,
        })
    except IntegrityError:
        await db.rollback()
        logger.warning(
            "No se pudo crear el usuario del portal de resultados para la empresa %s (login duplicado: %s)",
            enterprise.en_id, enterprise.en_nit,
        )
        return None

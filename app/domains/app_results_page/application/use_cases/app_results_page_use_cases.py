import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.app_results_page.domain.constants import ACCESS_TYPE_ENTERPRISE, ACCESS_TYPE_PATIENT
from app.domains.app_results_page.domain.models import AppResultsPage
from app.domains.app_results_page.infrastructure.repository import AppResultsPageRepository

logger = logging.getLogger(__name__)


async def _provision(
    db: AsyncSession,
    entity,
    origin_id: int,
    login: str | None,
    mail: str | None,
    access_type: int,
    label: str,
) -> AppResultsPage | None:
    """
    Crea el usuario del portal de resultados (idempotente). Nunca lanza excepción:
    si no se puede crear (login vacío o ya usado por otro registro) solo se registra
    un warning, para no tumbar la creación del paciente/empresa que ya quedó guardada.
    """
    existing = await AppResultsPageRepository.get_by_origin(db, origin_id, access_type)
    if existing:
        return existing

    if not login:
        logger.warning("No se creó el usuario del portal de resultados para %s %s: login vacío", label, origin_id)
        return None

    taken = await AppResultsPageRepository.get_by_login(db, login)
    if taken:
        logger.warning(
            "No se creó el usuario del portal de resultados para %s %s: el login %s ya pertenece a arp_user_id=%s",
            label, origin_id, login, taken.arp_user_id,
        )
        return None

    try:
        return await AppResultsPageRepository.create(db, {
            "arp_user_origin_id": origin_id,
            "arp_user_login": login,
            "arp_user_mail": mail,
            "arp_user_access_type": access_type,
        })
    except IntegrityError:
        await db.rollback()
        # El rollback expira los objetos de la sesión; se recarga la entidad (ya
        # confirmada) para que el llamador pueda seguir usándola sin lazy-load.
        await db.refresh(entity)
        logger.warning(
            "No se pudo crear el usuario del portal de resultados para %s %s (login duplicado: %s)",
            label, origin_id, login,
        )
        return None


async def provision_for_patient(db: AsyncSession, patient) -> AppResultsPage | None:
    """Crea el usuario del portal de resultados para un paciente recién creado (idempotente)."""
    return await _provision(
        db, patient, patient.pt_id, patient.pt_Number_document, patient.pt_mail,
        ACCESS_TYPE_PATIENT, "el paciente",
    )


async def provision_for_enterprise(db: AsyncSession, enterprise) -> AppResultsPage | None:
    """Crea el usuario del portal de resultados para una empresa recién creada (idempotente)."""
    return await _provision(
        db, enterprise, enterprise.en_id, enterprise.en_nit, enterprise.en_mail,
        ACCESS_TYPE_ENTERPRISE, "la empresa",
    )

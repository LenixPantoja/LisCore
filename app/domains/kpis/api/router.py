from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.kpis.api.schemas import ValidatedStudiesKpiResponse
from app.domains.kpis.application.use_cases import kpi_use_cases

router = APIRouter()

_CURRENT_YEAR = datetime.now().year


@router.get(
    "/validated-studies",
    response_model=ValidatedStudiesKpiResponse,
    summary="KPI – Estudios con resultados validados por mes",
    description=(
        "Retorna la cantidad de estudios con resultados validados agrupados por mes "
        "para el año indicado. Incluye todos los meses, con conteo 0 para los meses "
        "sin registros."
    ),
    dependencies=[Depends(require_permission("Kpis:ValidatedStudies"))],
)
async def get_validated_studies_kpi(
    year: int = Query(
        default=_CURRENT_YEAR,
        ge=2000,
        le=2100,
        description="Año a consultar (por defecto el año actual).",
    ),
    db: AsyncSession = Depends(get_db),
) -> ValidatedStudiesKpiResponse:
    return await kpi_use_cases.get_validated_studies_kpi(db, year)

from datetime import datetime, date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.kpis.api.schemas import (
    ValidatedStudiesKpiResponse,
    WeeklyTestsByAnalyzerResponse,
)
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


@router.get(
    "/weekly-tests-by-analyzer",
    response_model=WeeklyTestsByAnalyzerResponse,
    summary="KPI – Pruebas semanales por analizador en un rango de fechas",
    description=(
        "Retorna la cantidad semanal de pruebas registradas en Laboratories "
        "agrupadas por semana (inicia lunes) y por analizador (a_analyzer_result_id) "
        "dentro del rango de fechas especificado. "
        "Incluye el nombre del analizador desde la tabla Analizers. "
        "Los registros sin analizador asignado se agrupan como 'Sin asignar'. "
        "Solo cuenta pruebas con estado Validada (3) o Impreso (4)."
    ),
    dependencies=[Depends(require_permission("Kpis:DailyTestsByAnalyzer"))],
)
async def get_weekly_tests_by_analyzer_kpi(
    start_date: date = Query(
        ...,
        description="Fecha de inicio (YYYY-MM-DD). Ej: 2026-01-01",
    ),
    end_date: date = Query(
        ...,
        description="Fecha de fin (YYYY-MM-DD). Ej: 2026-06-11",
    ),
    db: AsyncSession = Depends(get_db),
) -> WeeklyTestsByAnalyzerResponse:
    return await kpi_use_cases.get_weekly_tests_by_analyzer_kpi(db, start_date, end_date)
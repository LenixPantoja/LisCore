from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.kpis.infrastructure.repository import KpiRepository
from app.domains.kpis.api.schemas import (
    ValidatedStudiesKpiResponse,
    ValidatedStudiesMonthItem,
    WeeklyTestsByAnalyzerResponse,
    WeeklyTestsByAnalyzerItem,
    MONTH_NAMES_ES,
)


async def get_validated_studies_kpi(
    db: AsyncSession,
    year: int,
) -> ValidatedStudiesKpiResponse:
    rows = await KpiRepository.get_validated_studies_by_month(db, year)

    month_map = {month: count for month, count in rows}

    data = [
        ValidatedStudiesMonthItem(
            month=m,
            month_name=MONTH_NAMES_ES[m],
            count=month_map.get(m, 0),
        )
        for m in range(1, 13)
    ]

    total = sum(item.count for item in data)

    return ValidatedStudiesKpiResponse(year=year, total=total, data=data)


async def get_weekly_tests_by_analyzer_kpi(
    db: AsyncSession,
    start_date: date,
    end_date: date,
) -> WeeklyTestsByAnalyzerResponse:
    """
    Retorna la cantidad semanal de pruebas registradas en Laboratories
    agrupadas por semana (inicia lunes) y por analizador (a_analyzer_result_id)
    dentro del rango de fechas especificado.

    Incluye un grupo "Sin asignar" para los registros sin analizador.
    Solo cuenta pruebas con estado Validada (3) o Impreso (4).
    """
    rows = await KpiRepository.get_weekly_tests_by_analyzer(db, start_date, end_date)

    data = [
        WeeklyTestsByAnalyzerItem(
            week_start=str(week_start),
            week_end=str(week_start + timedelta(days=6)),
            analyzer_id=analyzer_id,
            analyzer_name=analyzer_name,
            total_tests=total_tests,
        )
        for week_start, analyzer_id, analyzer_name, total_tests in rows
    ]

    total = sum(item.total_tests for item in data)

    return WeeklyTestsByAnalyzerResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        total=total,
        data=data,
    )
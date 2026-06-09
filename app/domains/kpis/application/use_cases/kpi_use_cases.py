from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.kpis.infrastructure.repository import KpiRepository
from app.domains.kpis.api.schemas import (
    ValidatedStudiesKpiResponse,
    ValidatedStudiesMonthItem,
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

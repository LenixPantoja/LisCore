from typing import List, Tuple
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, outerjoin, cast, Date

from app.domains.orders.domain.models import OrdersDetail
from app.domains.laboratories.domain.models import Laboratory
from app.domains.laboratories.domain.constants import (
    LABORATORY_STATE_VALIDADA,
    LABORATORY_STATE_IMPRESO,
)
from app.domains.analyzers.domain.models import Analyzer


class KpiRepository:
    @staticmethod
    async def get_validated_studies_by_month(
        db: AsyncSession,
        year: int,
    ) -> List[Tuple[int, int]]:
        """
        Returns a list of (month, count) tuples with the number of distinct
        validated studies (OrdersDetail) per month for the given year.

        A study is considered validated when at least one of its associated
        Laboratory records has l_state = VALIDADA and l_date_validatie in the
        requested year.
        """
        month_col = func.extract("month", Laboratory.l_date_validatie).label("month")

        stmt = (
            select(
                month_col,
                func.count(distinct(OrdersDetail.od_id)).label("count"),
            )
            .join(Laboratory, Laboratory.l_order_detail_id == OrdersDetail.od_id)
            .where(
                Laboratory.l_state == LABORATORY_STATE_VALIDADA,
                func.extract("year", Laboratory.l_date_validatie) == year,
                OrdersDetail.od_cancelled == 0,
            )
            .group_by(month_col)
            .order_by(month_col)
        )

        result = await db.execute(stmt)
        return [(int(row.month), int(row.count)) for row in result.all()]

    @staticmethod
    async def get_weekly_tests_by_analyzer(
        db: AsyncSession,
        start_date: date,
        end_date: date,
    ) -> List[Tuple[date, int, str, int]]:
        """
        Returns a list of (week_start, analyzer_id, analyzer_name, total_tests) tuples
        with the weekly count of laboratory records grouped by ISO week and analyzer,
        filtered by l_created_at within the given date range.

        Uses DATE_TRUNC('week') to group by week (Monday as start of week).
        Uses LEFT JOIN with Analyzers table to get the analyzer name.
        Records with a_analyzer_result_id = NULL are grouped as analyzer_id = 0
        with name "Sin asignar".
        Only counts records with l_state = 3 (Validated) or 4 (Printed).
        """
        filter_end = end_date + timedelta(days=1)

        week_col = func.date_trunc("week", Laboratory.l_created_at).label("week_start")
        analyzer_id_col = func.coalesce(Laboratory.a_analyzer_result_id, 0).label("analyzer_id")
        analyzer_name_col = func.coalesce(Analyzer.a_name, "Sin asignar").label("analyzer_name")

        stmt = (
            select(
                week_col,
                analyzer_id_col,
                analyzer_name_col,
                func.count(Laboratory.l_id).label("total_tests"),
            )
            .outerjoin(
                Analyzer,
                Laboratory.a_analyzer_result_id == Analyzer.a_id,
            )
            .where(
                Laboratory.l_created_at >= start_date,
                Laboratory.l_created_at < filter_end,
                Laboratory.l_state.in_([LABORATORY_STATE_VALIDADA, LABORATORY_STATE_IMPRESO]),
            )
            .group_by("week_start", "analyzer_id", "analyzer_name")
            .order_by("week_start", "analyzer_name")
        )

        result = await db.execute(stmt)
        return [
            (row.week_start, int(row.analyzer_id), str(row.analyzer_name), int(row.total_tests))
            for row in result.all()
        ]
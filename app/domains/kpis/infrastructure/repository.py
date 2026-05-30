from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct

from app.domains.orders.domain.models import OrdersDetail
from app.domains.laboratories.domain.models import Laboratory
from app.domains.laboratories.domain.constants import LABORATORY_STATE_VALIDADA


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

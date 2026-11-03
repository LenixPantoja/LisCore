from typing import List, Sequence, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, outerjoin, or_
from sqlalchemy import String
from sqlalchemy.sql.expression import cast

from app.domains.traces.models import AppTrace
from app.domains.traces.constants import (
    OPERATION_EDIT_RESULT,
    OPERATION_VALIDATE_RESULT,
    OPERATION_INVALIDATE_RESULT,
    OPERATION_VALIDATE_PRELIMINARY,
    OPERATION_INVALIDATE_PRELIMINARY,
)
from app.domains.users.infrastructure.models import AppUser

# Operaciones registradas por analito (no se muestran en la trazabilidad de la orden)
LABORATORY_OPERATIONS = (
    OPERATION_EDIT_RESULT,
    OPERATION_VALIDATE_RESULT,
    OPERATION_INVALIDATE_RESULT,
    OPERATION_VALIDATE_PRELIMINARY,
    OPERATION_INVALIDATE_PRELIMINARY,
)


def _user_full_name():
    """Expresión SQLAlchemy para el nombre completo del usuario."""
    from sqlalchemy import func as sa_func
    return (
        AppUser.usr_first_name
        + " "
        + AppUser.usr_last_name
    )


def _base_select():
    return (
        select(AppTrace, _user_full_name().label("user_full_name"))
        .outerjoin(AppUser, AppTrace.usr_id == AppUser.usr_id)
    )


class TraceRepository:

    @staticmethod
    async def get_by_order_id(
        db: AsyncSession,
        order_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Tuple[AppTrace, str]], int]:
        # Solo operaciones de la orden: las de cada analito (resultados y preliminares)
        # tienen su propio log por prueba (get_by_order_and_test).
        conditions = (
            AppTrace.order_id == order_id,
            AppTrace.test_id.is_(None),
            or_(AppTrace.operation_type.is_(None), AppTrace.operation_type.not_in(LABORATORY_OPERATIONS)),
        )
        base_query = _base_select().where(*conditions)

        count_stmt = select(func.count()).where(*conditions).select_from(AppTrace)
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            base_query.order_by(AppTrace.created_at.desc()).offset(skip).limit(limit)
        )
        return result.all(), total

    @staticmethod
    async def get_by_order_and_test(
        db: AsyncSession,
        order_id: int,
        test_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Tuple[AppTrace, str]], int]:
        base_query = (
            _base_select()
            .where(AppTrace.order_id == order_id, AppTrace.test_id == test_id)
        )

        count_stmt = (
            select(func.count())
            .where(AppTrace.order_id == order_id, AppTrace.test_id == test_id)
            .select_from(AppTrace)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            base_query.order_by(AppTrace.created_at.desc()).offset(skip).limit(limit)
        )
        return result.all(), total

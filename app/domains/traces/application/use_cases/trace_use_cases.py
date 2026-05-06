from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.traces.infrastructure.repository import TraceRepository
from app.domains.traces.api.schemas import TraceResponse, TracePaginatedResponse
from app.domains.traces.constants import OPERATION_TYPES


def _map_to_response(trace, user_full_name: str) -> TraceResponse:
    return TraceResponse(
        id=trace.id,
        user_name=user_full_name,
        order_id=trace.order_id,
        operation_name=OPERATION_TYPES.get(trace.operation_type, str(trace.operation_type))
        if trace.operation_type is not None
        else None,
        operation_description=trace.operation_description,
        notes=trace.notes,
        test_id=trace.test_id,
        created_at=trace.created_at,
    )


async def get_traces_by_order(
    db: AsyncSession,
    order_id: int,
    skip: int,
    limit: int,
) -> TracePaginatedResponse:
    rows, total = await TraceRepository.get_by_order_id(db, order_id, skip, limit)
    return TracePaginatedResponse(
        items=[_map_to_response(trace, user_full_name) for trace, user_full_name in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


async def get_traces_by_order_and_test(
    db: AsyncSession,
    order_id: int,
    test_id: int,
) -> List[TraceResponse]:
    rows = await TraceRepository.get_by_order_and_test(db, order_id, test_id)
    return [_map_to_response(trace, user_full_name) for trace, user_full_name in rows]

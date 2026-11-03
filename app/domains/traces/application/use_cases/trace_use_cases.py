from typing import Optional
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
    skip: int,
    limit: int,
) -> TracePaginatedResponse:
    rows, total = await TraceRepository.get_by_order_and_test(db, order_id, test_id, skip, limit)
    return TracePaginatedResponse(
        items=[_map_to_response(trace, user_full_name) for trace, user_full_name in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


async def register_result_delivery(
    db: AsyncSession,
    order_id: int,
    usr_id: int,
    receiver_name: str,
    relationship: str,
    document_number: str,
    study_codes: Optional[list[str]] = None,
    user_name: Optional[str] = None,
) -> TraceResponse:
    """Registra en la traza de la orden quién imprimió el resultado y quién lo recibió."""
    from fastapi import HTTPException, status
    from app.domains.orders.domain.models import Order
    from app.domains.traces.constants import OPERATION_PRINT_RESULT
    from utils.trace import register_trace

    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada.")

    receiver = f"{receiver_name.strip()} ({relationship.strip()}) - Doc. {document_number.strip()}"
    scope = f" | Estudios: {', '.join(study_codes)}" if study_codes else " | Todos los estudios"
    trace = await register_trace(
        db=db,
        operation_type=OPERATION_PRINT_RESULT,
        operation_description=f"Impresión de resultado - Entregado a: {receiver}",
        usr_id=usr_id,
        order_id=order_id,
        notes=f"Recibe: {receiver}{scope}",
    )
    await db.commit()
    return _map_to_response(trace, user_name)

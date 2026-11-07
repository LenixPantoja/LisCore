from fastapi import APIRouter, Depends, Query
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission, get_current_user
from app.domains.users.infrastructure.models import AppUser
from app.domains.traces.api.schemas import TraceResponse, TracePaginatedResponse, ResultDeliveryRequest, ResultDownloadRequest
from app.domains.traces.application.use_cases import trace_use_cases as use_cases

router = APIRouter()


@router.get("/order/{order_id}", response_model=TracePaginatedResponse,
            dependencies=[Depends(require_permission("Traces:Read"))])
async def get_traces_by_order(
    order_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.get_traces_by_order(db, order_id, skip, limit)


@router.get("/order/{order_id}/test/{test_id}", response_model=TracePaginatedResponse,
            dependencies=[Depends(require_permission("Traces:Read"))])
async def get_traces_by_order_and_test(
    order_id: int,
    test_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.get_traces_by_order_and_test(db, order_id, test_id, skip, limit)


@router.post("/order/{order_id}/result-delivery", response_model=TraceResponse)
async def register_result_delivery(
    order_id: int,
    data: ResultDeliveryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    """Registra la impresión del resultado y los datos de quien lo retira."""
    return await use_cases.register_result_delivery(
        db, order_id, current_user.usr_id,
        data.receiver_name, data.relationship, data.document_number, data.study_codes,
        user_name=f"{current_user.usr_first_name or ''} {current_user.usr_last_name or ''}".strip(),
    )


@router.post("/order/{order_id}/result-download", response_model=TraceResponse)
async def register_result_download(
    order_id: int,
    data: ResultDownloadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    """Registra en la traza de la orden la descarga del PDF del resultado."""
    return await use_cases.register_result_download(
        db, order_id, current_user.usr_id, data.study_codes,
        user_name=f"{current_user.usr_first_name or ''} {current_user.usr_last_name or ''}".strip(),
    )

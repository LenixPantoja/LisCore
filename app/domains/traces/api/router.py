from fastapi import APIRouter, Depends, Query
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.traces.api.schemas import TraceResponse, TracePaginatedResponse
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

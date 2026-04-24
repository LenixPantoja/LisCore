from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.domains.orders.api.schemas import (
    OrderCreate, OrderUpdate, OrderResponse, OrderPaginatedResponse, 
    NextOrderNumberResponse, OrderDetailsPaginatedResponse, OrderFullDetailsResponse,
    OrderCreatedResponse
)
from app.domains.orders.application.use_cases import order_use_cases as use_cases

router = APIRouter()

@router.post("/", response_model=OrderCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_order(db, data.model_dump())

@router.get("/", response_model=OrderPaginatedResponse)
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await use_cases.list_orders(db, skip, limit, search)

@router.get("/next-number", response_model=NextOrderNumberResponse)
async def get_next_order_number(db: AsyncSession = Depends(get_db)):
    """
    Get the next order number (last order ID + 1).

    Informative endpoint only - does not create an order.
    """
    return await use_cases.get_next_order_number(db)

@router.get("/{id}", response_model=OrderResponse)
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_order_by_id(db, id)

@router.patch("/{id}", response_model=OrderResponse)
async def update(id: int, data: OrderUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_order(db, id, data.model_dump(exclude_unset=True))

@router.get("/by-number/{o_number}/details", response_model=OrderDetailsPaginatedResponse)
async def get_order_details_paginated(
    o_number: str,
    skip_labs: int = Query(0, ge=0),
    limit_labs: int = Query(100, ge=1, le=500),
    skip_tests: int = Query(0, ge=0),
    limit_tests: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get an order by number with its paginated laboratories and tests.
    """
    return await use_cases.get_order_details_paginated_by_number(
        db, o_number, skip_labs, limit_labs, skip_tests, limit_tests
    )

@router.get("/{id}/full", response_model=OrderFullDetailsResponse)
async def get_full_order_by_id(id: int, db: AsyncSession = Depends(get_db)):
    """
    Get full details of an order including all non-paginated children arrays.
    """
    return await use_cases.get_full_order_details_by_id(db, id)
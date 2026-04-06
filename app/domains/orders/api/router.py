from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.domains.orders.api.schemas import OrderCreate, OrderUpdate, OrderResponse
from app.domains.orders.application.use_cases import order_use_cases as use_cases

router = APIRouter()

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_order(db, data.model_dump())

@router.get("/", response_model=List[OrderResponse])
async def list_all(db: AsyncSession = Depends(get_db)):
    return await use_cases.list_orders(db)

@router.get("/{id}", response_model=OrderResponse)
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_order_by_id(db, id)

@router.patch("/{id}", response_model=OrderResponse)
async def update(id: int, data: OrderUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_order(db, id, data.model_dump(exclude_unset=True))
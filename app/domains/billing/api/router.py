from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.domains.billing.api.schemas import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoicePaginatedResponse,
)
from app.domains.billing.application.use_cases import invoice_use_cases as use_cases

router = APIRouter()


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create(data: InvoiceCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_invoice(db, data.model_dump())


@router.get("/", response_model=InvoicePaginatedResponse)
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.list_invoices(db, skip, limit, search)


@router.get("/{id}", response_model=InvoiceResponse)
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_invoice_by_id(db, id)


@router.patch("/{id}", response_model=InvoiceResponse)
async def update(id: int, data: InvoiceUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_invoice(db, id, data.model_dump(exclude_unset=True))


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.delete_invoice(db, id)

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.domains.billing.infrastructure.repository import InvoiceRepository
from app.domains.billing.api.schemas import InvoiceCreate, InvoiceUpdate


async def create_invoice(db: AsyncSession, data: dict) -> dict:
    details_raw = data.pop("details", [])
    details = [d if isinstance(d, dict) else d for d in details_raw]

    invoice = await InvoiceRepository.create(db, data, details)
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def list_invoices(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> dict:
    items, total = await InvoiceRepository.get_paginated(db, skip, limit, search)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


async def get_invoice_by_id(db: AsyncSession, inv_id: int):
    invoice = await InvoiceRepository.get_by_id(db, inv_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {inv_id} not found.",
        )
    return invoice


async def update_invoice(db: AsyncSession, inv_id: int, update_data: dict):
    invoice = await InvoiceRepository.update(db, inv_id, update_data)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {inv_id} not found.",
        )
    return invoice


async def delete_invoice(db: AsyncSession, inv_id: int) -> dict:
    deleted = await InvoiceRepository.delete(db, inv_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {inv_id} not found.",
        )
    return {"detail": f"Invoice {inv_id} deleted successfully."}

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from app.domains.billing.domain.constants import INVOICE_STATES, INVOICE_TYPES, INVOICE_SUB_TYPES


# ── Invoice Detail ────────────────────────────────────────────────────────────

class InvoiceDetailBase(BaseModel):
    invd_order_detail_id: Optional[int] = None
    invd_study_id: Optional[int] = None
    invd_value: Optional[Decimal] = None
    invd_discount: Optional[Decimal] = None
    invd_total: Optional[Decimal] = None


class InvoiceDetailCreate(InvoiceDetailBase):
    pass


class InvoiceDetailUpdate(BaseModel):
    invd_value: Optional[Decimal] = None
    invd_discount: Optional[Decimal] = None
    invd_total: Optional[Decimal] = None


class InvoiceDetailResponse(InvoiceDetailBase):
    invd_id: int
    invd_invoice_id: Optional[int] = None
    invd_created_by: Optional[int] = None
    invd_created_at: Optional[datetime] = None
    invd_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Invoice ───────────────────────────────────────────────────────────────────

class InvoiceBase(BaseModel):
    inv_number: Optional[str] = None
    inv_date: Optional[date] = None
    inv_due_date: Optional[date] = None
    inv_enterprise_id: Optional[int] = None
    inv_patient_id: Optional[int] = None
    inv_contract_id: Optional[int] = None
    inv_subtotal: Optional[Decimal] = None
    inv_tax: Optional[Decimal] = None
    inv_total: Optional[Decimal] = None
    inv_state: Optional[int] = None
    inv_type: Optional[int] = None
    inv_sub_type_invoice: Optional[int] = None
    inv_notes: Optional[str] = None
    tariff_id: Optional[int] = None


class InvoiceCreate(InvoiceBase):
    details: Optional[List[InvoiceDetailCreate]] = []


class InvoiceUpdate(BaseModel):
    inv_number: Optional[str] = None
    inv_date: Optional[date] = None
    inv_due_date: Optional[date] = None
    inv_enterprise_id: Optional[int] = None
    inv_patient_id: Optional[int] = None
    inv_contract_id: Optional[int] = None
    inv_subtotal: Optional[Decimal] = None
    inv_tax: Optional[Decimal] = None
    inv_total: Optional[Decimal] = None
    inv_state: Optional[int] = None
    inv_type: Optional[int] = None
    inv_sub_type_invoice: Optional[int] = None
    inv_notes: Optional[str] = None
    tariff_id: Optional[int] = None


class InvoiceResponse(InvoiceBase):
    inv_id: int
    inv_created_by: Optional[int] = None
    inv_created_at: Optional[date] = None
    inv_updated_at: Optional[date] = None
    details: List[InvoiceDetailResponse] = []

    # Human-readable labels (override int fields in response)
    inv_state_name: Optional[str] = None
    inv_type_name: Optional[str] = None
    inv_sub_type_name: Optional[str] = None

    @field_validator("inv_state_name", mode="before")
    @classmethod
    def _resolve_state(cls, v, info):
        raw = info.data.get("inv_state")
        if raw is None:
            return None
        return INVOICE_STATES.get(raw, str(raw))

    @field_validator("inv_type_name", mode="before")
    @classmethod
    def _resolve_type(cls, v, info):
        raw = info.data.get("inv_type")
        if raw is None:
            return None
        return INVOICE_TYPES.get(raw, str(raw))

    @field_validator("inv_sub_type_name", mode="before")
    @classmethod
    def _resolve_sub_type(cls, v, info):
        raw = info.data.get("inv_sub_type_invoice")
        if raw is None:
            return None
        return INVOICE_SUB_TYPES.get(raw, str(raw))

    class Config:
        from_attributes = True


class InvoicePaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[InvoiceResponse]

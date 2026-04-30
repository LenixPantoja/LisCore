from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

from app.domains.requests.domain.constants import INBOUND_ORDER_DETAIL_STATES


# ─────────────────────────────────────────────
# InboundOrderDetail schemas
# ─────────────────────────────────────────────

class InboundOrderDetailBase(BaseModel):
    iod_study_id: Optional[int] = None
    iod_state: Optional[int] = None
    iod_observation: Optional[str] = None
    iod_laboratory_id: Optional[int] = None
    iod_order_id: Optional[int] = None
    iod_study_consecutive: Optional[str] = None


class InboundOrderDetailCreate(InboundOrderDetailBase):
    pass


class InboundOrderDetailUpdate(BaseModel):
    iod_state: Optional[int] = None
    iod_observation: Optional[str] = None
    iod_laboratory_id: Optional[int] = None
    iod_order_id: Optional[int] = None
    iod_study_consecutive: Optional[str] = None


class InboundOrderDetailResponse(InboundOrderDetailBase):
    iod_id: int
    iod_inboundOrder_id: Optional[int] = None
    iod_state: Optional[str] = None  # serializado como nombre del estado
    iod_created_at: Optional[datetime] = None
    iod_updated_at: Optional[datetime] = None

    @field_validator("iod_state", mode="before")
    @classmethod
    def convert_state(cls, v):
        if isinstance(v, int):
            return INBOUND_ORDER_DETAIL_STATES.get(v, str(v))
        return v

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# InboundOrder schemas
# ─────────────────────────────────────────────

class InboundOrderBase(BaseModel):
    io_number_request: Optional[str] = None
    io_date_request: Optional[datetime] = None
    io_date_transmission: Optional[datetime] = None
    io_patient_id: Optional[int] = None
    io_tariff_id: Optional[int] = None
    io_service_id: Optional[int] = None
    io_diagnostic_id: Optional[int] = None
    io_origin: Optional[str] = None
    io_priority: Optional[int] = None
    io_medic_document_number: Optional[str] = None
    io_medic_name: Optional[str] = None
    io_headquarter_id: Optional[int] = None
    io_country_id: Optional[int] = None
    io_income: Optional[str] = None
    io_enterprise_id: Optional[int] = None
    io_municipality_id: Optional[int] = None
    io_scholarity_id: Optional[int] = None


class InboundOrderCreate(InboundOrderBase):
    details: List[InboundOrderDetailCreate] = []


class InboundOrderUpdate(BaseModel):
    io_number_request: Optional[str] = None
    io_date_request: Optional[datetime] = None
    io_date_transmission: Optional[datetime] = None
    io_patient_id: Optional[int] = None
    io_tariff_id: Optional[int] = None
    io_service_id: Optional[int] = None
    io_diagnostic_id: Optional[int] = None
    io_origin: Optional[str] = None
    io_priority: Optional[int] = None
    io_medic_document_number: Optional[str] = None
    io_medic_name: Optional[str] = None
    io_headquarter_id: Optional[int] = None
    io_country_id: Optional[int] = None
    io_income: Optional[str] = None
    io_enterprise_id: Optional[int] = None
    io_municipality_id: Optional[int] = None
    io_scholarity_id: Optional[int] = None


class InboundOrderResponse(InboundOrderBase):
    io_id: int
    io_created_at: Optional[datetime] = None
    io_updated_at: Optional[datetime] = None
    details: List[InboundOrderDetailResponse] = []

    model_config = {"from_attributes": True}


class InboundOrderPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[InboundOrderResponse]

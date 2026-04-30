from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

from app.domains.requests.domain.constants import INBOUND_ORDER_DETAIL_STATES

PRIORITY_LABELS: dict[int, str] = {0: "Normal", 1: "Urgente", 2: "Muy Urgente"}


class SampleTypeInfo(BaseModel):
    st_id: Optional[int] = None
    st_name: Optional[str] = None
    st_color: Optional[str] = None

    model_config = {"from_attributes": True}


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


class InboundOrderDetailResponse(BaseModel):
    iod_id: int
    iod_inboundOrder_id: Optional[int] = None
    iod_study_id: Optional[int] = None
    iod_state: Optional[str] = None  # serializado como nombre del estado
    iod_observation: Optional[str] = None
    iod_laboratory_id: Optional[int] = None
    iod_order_id: Optional[int] = None
    iod_study_consecutive: Optional[str] = None
    iod_created_at: Optional[datetime] = None
    iod_updated_at: Optional[datetime] = None

    # Datos del estudio
    study_name: Optional[str] = None
    study_code: Optional[str] = None
    sample_types: List[SampleTypeInfo] = []

    @field_validator("iod_state", mode="before")
    @classmethod
    def convert_state(cls, v):
        if isinstance(v, int):
            return INBOUND_ORDER_DETAIL_STATES.get(v, str(v))
        return v

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_names(cls, detail):
        study = detail.study
        sample_types = []
        if study and study.test_details:
            seen = set()
            for td in study.test_details:
                if td.test and td.test.sample_type:
                    st = td.test.sample_type
                    if st.st_id not in seen:
                        seen.add(st.st_id)
                        sample_types.append(
                            SampleTypeInfo(
                                st_id=st.st_id,
                                st_name=st.st_name,
                                st_color=st.st_color,
                            )
                        )

        return cls(
            iod_id=detail.iod_id,
            iod_inboundOrder_id=detail.iod_inboundOrder_id,
            iod_study_id=detail.iod_study_id,
            iod_state=detail.iod_state,
            iod_observation=detail.iod_observation,
            iod_laboratory_id=detail.iod_laboratory_id,
            iod_order_id=detail.iod_order_id,
            iod_study_consecutive=detail.iod_study_consecutive,
            iod_created_at=detail.iod_created_at,
            iod_updated_at=detail.iod_updated_at,
            study_name=study.name if study else None,
            study_code=study.code if study else None,
            sample_types=sample_types,
        )


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

    # Nombres de relaciones
    patient_name: Optional[str] = None
    patient_document: Optional[str] = None
    sex_code: Optional[str] = None
    tariff_name: Optional[str] = None
    service_name: Optional[str] = None
    diagnosis_code: Optional[str] = None
    diagnosis_description: Optional[str] = None
    headquarter_name: Optional[str] = None
    enterprise_name: Optional[str] = None
    scholarity_description: Optional[str] = None
    priority_name: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_names(cls, order):
        patient = order.patient
        parts = []
        if patient:
            parts = [
                patient.pt_firts_name or "",
                getattr(patient, "pt_middle_name", "") or "",
                patient.pt_last_name or "",
                getattr(patient, "pt_second_last_name", "") or "",
            ]
        patient_name = " ".join(p for p in parts if p).strip() or None
        patient_document = patient.pt_Number_document if patient else None

        details = [
            InboundOrderDetailResponse.from_orm_with_names(d) for d in order.details
        ]

        return cls(
            io_id=order.io_id,
            io_number_request=order.io_number_request,
            io_date_request=order.io_date_request,
            io_date_transmission=order.io_date_transmission,
            io_patient_id=order.io_patient_id,
            io_tariff_id=order.io_tariff_id,
            io_service_id=order.io_service_id,
            io_diagnostic_id=order.io_diagnostic_id,
            io_origin=order.io_origin,
            io_priority=order.io_priority,
            io_medic_document_number=order.io_medic_document_number,
            io_medic_name=order.io_medic_name,
            io_headquarter_id=order.io_headquarter_id,
            io_country_id=order.io_country_id,
            io_income=order.io_income,
            io_enterprise_id=order.io_enterprise_id,
            io_municipality_id=order.io_municipality_id,
            io_scholarity_id=order.io_scholarity_id,
            io_created_at=order.io_created_at,
            io_updated_at=order.io_updated_at,
            details=details,
            patient_name=patient_name,
            patient_document=patient_document,
            sex_code=patient.sex_type.code if patient and patient.sex_type else None,
            tariff_name=order.tariff.t_name if order.tariff else None,
            service_name=order.service.name if order.service else None,
            diagnosis_code=order.diagnosis.diag_code if order.diagnosis else None,
            diagnosis_description=order.diagnosis.d_description if order.diagnosis else None,
            headquarter_name=order.headquarter.name if order.headquarter else None,
            enterprise_name=order.enterprise.en_name if order.enterprise else None,
            scholarity_description=order.scholarity.description if order.scholarity else None,
            priority_name=PRIORITY_LABELS.get(order.io_priority, None) if order.io_priority is not None else None,
        )


class InboundOrderPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[InboundOrderResponse]


# ─────────────────────────────────────────────
# Create Order from InboundOrder schemas
# ─────────────────────────────────────────────

class CreateOrderFromInboundRequest(BaseModel):
    inbound_order_id: int
    inbound_detail_ids: List[int]
    o_headquarter_id: Optional[int] = None
    o_AppUser_id: Optional[int] = None


class CreateOrderFromInboundResponse(BaseModel):
    o_id: int
    o_number: str
    inbound_order_id: int
    updated_detail_ids: List[int]

    model_config = {"from_attributes": True}


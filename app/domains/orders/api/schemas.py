from pydantic import BaseModel, EmailStr, field_validator, Field, computed_field
from typing import Optional, List, Any
from datetime import date, datetime
from app.domains.patients.api.schemas import PatientResponse
from app.domains.testslabs.api.schemas import TestsLabResponse
from app.domains.studieslab.api.schemas import StudiesLabResponse
from app.domains.enterprises.api.schemas import EnterpriseResponse
from app.domains.masters.api.schemas import ServiceResponse, DiagnosisResponse, SchoolingResponse
from app.domains.samples.api.schemas import SampleTypeResponse
from app.domains.orders.domain.constants import ORDER_STATES, ORDER_DETAIL_STATES
from app.domains.samples.domain.constants import SAMPLE_ORDER_STATES
from app.domains.laboratories.domain.constants import LABORATORY_STATES
class OrderBase(BaseModel):
    o_number: str
    o_date: date
    o_his_id: int
    o_age: Optional[str] = None
    o_pregnated: Optional[bool] = False
    o_week_pregnated: Optional[str] = None
    o_priority: Optional[int] = 0
    o_autorizacion: Optional[str] = None
    o_service_id: Optional[int] = None
    o_diagnoses_id: Optional[int] = None
    o_headquarter_id: Optional[int] = None
    o_AppUser_id: Optional[int] = None
    o_enterprise_id: Optional[int] = None
    o_scholarity: Optional[int] = None
    o_order_state: Optional[int] = 1
    o_pat_num_whatsapp: Optional[str] = None
    o_pat_mail: Optional[EmailStr] = None
    o_note: Optional[str] = None
    o_tariff_id: Optional[int] = None
    o_sample_name: Optional[str] = None

class OrderCreate(OrderBase):
    """Esquema para crear una orden con sus estudios solicitados."""
    o_date: Optional[date] = None  # Se asigna automáticamente si no se envía
    studies: List[int]

class OrderUpdate(BaseModel):
    o_print_date: Optional[datetime] = None
    o_pregnated: Optional[bool] = None
    o_week_pregnated: Optional[str] = None
    o_priority: Optional[int] = None
    o_mail_sent: Optional[int] = None
    o_whatsapp_sent: Optional[int] = None
    o_autorizacion: Optional[str] = None
    o_order_state: Optional[int] = None
    o_pat_num_whatsapp: Optional[str] = None
    o_pat_mail: Optional[EmailStr] = None
    o_note: Optional[str] = None

class OrderResponse(OrderBase):
    o_id: int
    o_print_date: Optional[datetime] = None
    o_mail_sent: int
    o_whatsapp_sent: int
    o_created_at: datetime
    o_updated_at: datetime
    o_order_state: Optional[str] = None  # Override: se serializa como nombre del estado
    patient: Optional[PatientResponse] = None

    @field_validator('o_order_state', mode='before')
    @classmethod
    def convert_o_order_state(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return ORDER_STATES.get(v, str(v))
        return v

    @computed_field
    @property
    def patient_document(self) -> Optional[str]:
        if not self.patient:
            return None
        return self.patient.pt_Number_document

    @computed_field
    @property
    def patient_full_name(self) -> Optional[str]:
        if not self.patient:
            return None
        parts = [
            self.patient.pt_firts_name,
            self.patient.pt_middle_name,
            self.patient.pt_last_name,
            self.patient.pt_second_last_name,
        ]
        return " ".join(part for part in parts if part)

    class Config:
        from_attributes = True

class OrderPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[OrderResponse]

class NextOrderNumberResponse(BaseModel):
    next_order_number: str

class OrderCreatedResponse(BaseModel):
    """Response returned immediately after a successful order creation."""
    o_id: int
    o_number: str
    o_date: Optional[date] = None
    o_his_id: int
    o_enterprise_id: Optional[int] = None
    o_tariff_id: Optional[int] = None
    o_order_state: Optional[str] = None
    o_created_at: Optional[datetime] = None

    @field_validator('o_order_state', mode='before')
    @classmethod
    def convert_o_order_state(cls, v):
        if isinstance(v, int):
            return ORDER_STATES.get(v, str(v))
        return v

    class Config:
        from_attributes = True

# Nuevos esquemas añadidos para los casos de uso solicitados

class PatientOrderListItem(BaseModel):
    o_id: int
    pt_Number_document: str
    pt_Document_Type_id: Optional[int] = None
    o_number: str
    o_date: date
    patient_full_name: str
    o_order_state: int
    order_state_name: str

    class Config:
        from_attributes = True

class PatientOrdersPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[PatientOrderListItem]

class BasicStudiesLabResponse(BaseModel):
    id: int
    code: str
    name: str

    class Config:
        from_attributes = True

class BasicUserResponse(BaseModel):
    usr_id: int
    usr_first_name: str
    usr_last_name: str
    usr_middle_name: Optional[str] = None
    usr_second_last_name: Optional[str] = None

    class Config:
        from_attributes = True

class UserValidationResponse(BaseModel):
    username: Optional[str] = Field(None, alias="usr_login")

    class Config:
        from_attributes = True
        populate_by_name = True

class BasicOrdersDetailResponse(BaseModel):
    od_id: int
    od_order_id: int
    od_study_id: int
    od_state: Optional[str] = None  # Serializado como nombre del estado
    study: Optional[BasicStudiesLabResponse] = None

    @field_validator('od_state', mode='before')
    @classmethod
    def convert_od_state(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return ORDER_DETAIL_STATES.get(v, str(v))
        return v

    class Config:
        from_attributes = True


class LaboratoryPreliminaryResponse(BaseModel):
    """Resultado preliminar de un laboratorio (ej. microbiología)."""
    lp_id: int
    lp_laboratory_id: int
    lp_secuence: int
    lp_result: Optional[str] = None
    lp_date_preliminary: Optional[str] = None
    analyzer: Optional[str] = None
    lp_state: int

    @field_validator('lp_date_preliminary', mode='before')
    @classmethod
    def format_datetime_with_ampm(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v
        # v es un datetime object → formatear con AM/PM
        return v.strftime("%Y-%m-%d %I:%M:%S %p")

    class Config:
        from_attributes = True


class ReferenceValueEntry(BaseModel):
    range_type: Optional[str] = None
    gender: Optional[str] = None
    age_type: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    text_value: Optional[str] = None


class LaboratoryResponse(BaseModel):
    l_id: int
    l_order_detail_id: Optional[int] = None
    l_test_id: Optional[int] = None
    l_result: Optional[str] = None
    l_result_num: Optional[float] = None
    l_result_comp: Optional[str] = None
    l_result_graphic: Optional[str] = None
    l_nota_validation: Optional[str] = None
    l_state: Optional[str] = None  # Serializado como nombre del estado
    l_date_transmited: Optional[datetime] = None
    l_date_validatie: Optional[datetime] = None
    l_user_validation_id: Optional[int] = None
    a_analyzer_result_id: Optional[int] = None
    l_created_at: datetime
    l_updated_at: datetime

    # Campos de rango de referencia (calculados al consultar, no almacenados en BD)
    range_type: Optional[str] = None
    value_range_reference_min: Optional[float] = None
    value_range_reference_max: Optional[float] = None
    list_references_values: List[ReferenceValueEntry] = []

    order_detail: Optional[BasicOrdersDetailResponse] = None
    test: Optional[TestsLabResponse] = None
    user_validation: Optional[UserValidationResponse] = None
    preliminaries: List["LaboratoryPreliminaryResponse"] = []

    @field_validator('l_state', mode='before')
    @classmethod
    def convert_l_state(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return LABORATORY_STATES.get(v, str(v))
        return v

    class Config:
        from_attributes = True

class OrderDetailsLabsPaginated(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[LaboratoryResponse]

class OrderDetailsTestsPaginated(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[TestsLabResponse]

class OrderDetailsPaginatedResponse(BaseModel):
    order: OrderResponse
    patient: PatientResponse
    laboratories: OrderDetailsLabsPaginated
    tests: OrderDetailsTestsPaginated
    samples: List["SamplesOrderResponse"] = []

class TariffBasicResponse(BaseModel):
    t_id: int
    t_name: Optional[str] = None
    t_description: Optional[str] = None
    t_activo: Optional[bool] = None

    class Config:
        from_attributes = True


class SamplesOrderResponse(BaseModel):
    so_id: int
    so_order_id: Optional[int] = None
    so_sample_type_id: Optional[int] = None
    so_barcode: Optional[str] = None
    so_state: Optional[str] = None  # Serializado como nombre del estado
    so_number_studies: Optional[int] = None
    so_current_location_id: Optional[int] = None
    so_created_at: datetime
    so_updated_at: datetime
    sample_type: Optional[SampleTypeResponse] = None

    @field_validator('so_state', mode='before')
    @classmethod
    def convert_so_state(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return SAMPLE_ORDER_STATES.get(v, str(v))
        return v

    class Config:
        from_attributes = True


class OrderWithRelationsResponse(OrderResponse):
    service: Optional[ServiceResponse] = None
    diagnosis: Optional[DiagnosisResponse] = None
    enterprise: Optional[EnterpriseResponse] = None
    schooling: Optional[SchoolingResponse] = None
    tariff: Optional[TariffBasicResponse] = None
    details: Optional[List[BasicOrdersDetailResponse]] = None


class StudyWithLabsResponse(BaseModel):
    study_id: int
    study_name: Optional[str] = None
    study_code: Optional[str] = None
    study_value: Optional[Any] = None
    od_cancelled: int = 0
    study_state: Optional[str] = None
    laboratories: List["SlimLaboratoryResponse"] = []


class SlimLaboratoryResponse(BaseModel):
    """Lab sin order_detail (el estudio es el padre en laboratories_by_study)."""
    l_id: int
    l_order_detail_id: Optional[int] = None
    l_test_id: Optional[int] = None
    l_result: Optional[str] = None
    l_result_num: Optional[float] = None
    l_result_comp: Optional[str] = None
    l_result_graphic: Optional[str] = None
    l_nota_validation: Optional[str] = None
    l_state: Optional[str] = None
    l_date_transmited: Optional[datetime] = None
    l_date_validatie: Optional[datetime] = None
    l_user_validation_id: Optional[int] = None
    a_analyzer_result_id: Optional[int] = None
    l_created_at: datetime
    l_updated_at: datetime

    # Campos de rango de referencia (calculados al consultar, no almacenados en BD)
    range_type: Optional[str] = None
    value_range_reference_min: Optional[float] = None
    value_range_reference_max: Optional[float] = None

    test: Optional[TestsLabResponse] = None
    user_validation: Optional[UserValidationResponse] = None
    preliminaries: List["LaboratoryPreliminaryResponse"] = []

    @field_validator('l_state', mode='before')
    @classmethod
    def convert_l_state(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return LABORATORY_STATES.get(v, str(v))
        return v

    class Config:
        from_attributes = True


StudyWithLabsResponse.model_rebuild()


class OrderSummaryForFullResponse(OrderResponse):
    """OrderWithRelations sin 'details' para evitar duplicados en /full."""
    service: Optional[ServiceResponse] = None
    diagnosis: Optional[DiagnosisResponse] = None
    enterprise: Optional[EnterpriseResponse] = None
    schooling: Optional[SchoolingResponse] = None
    tariff: Optional[TariffBasicResponse] = None


class InvoiceSummaryResponse(BaseModel):
    inv_id: int
    inv_number: Optional[str] = None
    inv_subtotal: Optional[Any] = None
    inv_tax: Optional[Any] = None
    inv_total: Optional[Any] = None
    inv_state: Optional[int] = None
    inv_state_name: Optional[str] = None
    inv_type: Optional[int] = None
    inv_type_name: Optional[str] = None
    inv_sub_type_invoice: Optional[int] = None
    inv_sub_type_name: Optional[str] = None


class HeadquarterBasicResponse(BaseModel):
    id: int
    name: Optional[str] = None
    address: Optional[str] = None
    prefix: Optional[str] = None

    class Config:
        from_attributes = True


class OrderFullDetailsResponse(BaseModel):
    order: OrderSummaryForFullResponse
    patient: PatientResponse
    headquarter: Optional[HeadquarterBasicResponse] = None
    studies: List[StudyWithLabsResponse] = []
    samples: List[SamplesOrderResponse]
    invoice: Optional[InvoiceSummaryResponse] = None


# ── Gráfico evolutivo de resultados ──────────────────────────────────────────

class HistoricoResultadoItem(BaseModel):
    fecha: Optional[datetime] = None
    valor: Optional[float] = None
    referencia_min: Optional[float] = None
    referencia_max: Optional[float] = None
    estado: Optional[str] = None
    orden_numero: Optional[str] = None


class GraficoEvolutivoResponse(BaseModel):
    prueba: Optional[str] = None
    codigo: Optional[str] = None
    unidad: Optional[str] = None
    paciente: Optional[str] = None
    historico: List[HistoricoResultadoItem] = []


class OrderEditRequest(BaseModel):
    """Esquema para editar campos de una orden y/o agregar estudios."""
    o_enterprise_id: Optional[int] = None
    o_diagnoses_id: Optional[int] = None
    o_service_id: Optional[int] = None
    o_autorizacion: Optional[str] = None
    o_pregnated: Optional[bool] = None
    o_week_pregnated: Optional[str] = None
    o_priority: Optional[int] = None
    o_scholarity: Optional[int] = None
    o_note: Optional[str] = None
    o_tariff_id: Optional[int] = None
    studies: Optional[List[int]] = None  # IDs de estudios a agregar


class OrderEditResponse(BaseModel):
    success: bool
    o_id: int
    updated_fields: List[str]
    added_studies: List[int]
    skipped_studies: List[int]
    invalid_studies: List[int]
    message: str


class CancelStudiesRequest(BaseModel):
    study_ids: List[int] = Field(..., min_length=1, description="IDs de los estudios a anular.")


class CancelStudiesResponse(BaseModel):
    success: bool
    o_id: int
    cancelled_detail_ids: List[int]
    order_cancelled: bool
    message: str


# ── Filtros de órdenes ───────────────────────────────────────────────────────

class OrderFilterRequest(BaseModel):
    """
    Esquema para filtrar órdenes por múltiples criterios.

    - start_date / end_date: Rango de fecha/hora (o_created_at). Acepta solo
      fecha ("2026-07-28") o fecha y hora en formato de 12 horas
      ("07/28/2026 02:30 PM" / "28/07/2026 02:30 PM"). Si end_date viene sin
      hora, incluye todo ese día.
    - order_states: Lista de estados de la orden (1=Ingresada, 2=Pendiente, 3=Con Resultados, 4=Validada, 5=Impresa, 6=Cerrada, 7=Anulada)
    - work_group_ids: Lista de IDs de grupos de trabajo (Work_groups.wg_id)
    - study_ids: Lista de IDs de estudios (StudiesLab.id)
    """
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    order_states: Optional[List[int]] = None
    work_group_ids: Optional[List[int]] = None
    study_ids: Optional[List[int]] = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _parse_flexible_datetime(cls, v):
        """Acepta datetime/date ya parseados, o texto en formato de 12 horas o solo fecha."""
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime.combine(v, datetime.min.time())
        text = str(v).strip()
        if not text:
            return None
        for fmt in (
            "%m/%d/%Y %I:%M %p",
            "%d/%m/%Y %I:%M %p",
            "%Y-%m-%d %I:%M %p",
            "%m/%d/%Y %I:%M:%S %p",
            "%d/%m/%Y %I:%M:%S %p",
            "%Y-%m-%d %I:%M:%S %p",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        raise ValueError(
            f"Formato de fecha/hora inválido: '{v}'. Usa 'MM/DD/AAAA hh:mm AM/PM' (ej. '07/28/2026 02:30 PM') o 'AAAA-MM-DD'."
        )


class OrderFilterItemResponse(BaseModel):
    """
    Respuesta individual de una orden filtrada.
    """
    o_id: int
    o_number: str
    pt_name: str = Field(..., description="Nombre completo del paciente: Nombre1 Nombre2 Apellido1 Apellido2")
    pt_number_document: str

    class Config:
        from_attributes = True

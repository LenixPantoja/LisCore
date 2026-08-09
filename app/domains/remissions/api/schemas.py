from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


# ── External Reference Laboratories ────────────────────────────────────

class ExternalLabCreateRequest(BaseModel):
    erl_nit: str
    erl_name: str
    erl_address: Optional[str] = None
    erl_phone: Optional[str] = None
    erl_mail: Optional[str] = None
    erl_active: bool = True


class ExternalLabUpdateRequest(BaseModel):
    erl_nit: Optional[str] = None
    erl_name: Optional[str] = None
    erl_address: Optional[str] = None
    erl_phone: Optional[str] = None
    erl_mail: Optional[str] = None
    erl_active: Optional[bool] = None


class ExternalLabResponse(BaseModel):
    erl_id: int
    erl_nit: str
    erl_name: str
    erl_address: Optional[str] = None
    erl_phone: Optional[str] = None
    erl_mail: Optional[str] = None
    erl_active: bool
    erl_created_at: datetime
    erl_updated_at: datetime

    class Config:
        from_attributes = True


class ExternalLabListResponse(BaseModel):
    items: List[ExternalLabResponse]
    total: int


# ── Remission Items ────────────────────────────────────────────────────

class RemissionItemRequest(BaseModel):
    remd_sample_order_id: int
    remd_order_detail_id: int


class AddItemsRequest(BaseModel):
    items: List[RemissionItemRequest]


class AddItemsByBarcodeRequest(BaseModel):
    """
    Recibe el código de barras de la muestra (por ejemplo: 060600022613).
    Los primeros 10 dígitos corresponden al número de orden,
    los siguientes dígitos corresponden al sufijo del tipo de muestra.
    """
    sample_barcode: str


class RemissionDetailResponse(BaseModel):
    remd_id: int
    remd_remission_id: int
    remd_sample_order_id: int
    remd_order_detail_id: int
    remd_item_state: int
    remd_rejection_reason: Optional[str] = None
    remd_received_by_user_id: Optional[int] = None
    remd_updated_at: datetime

    class Config:
        from_attributes = True


# ── Remission Header ───────────────────────────────────────────────────

class RemissionCreateRequest(BaseModel):
    rem_type: str = Field(..., description="'LOCAL' o 'EXTERNAL'")
    rem_origin_headquarter_id: int
    rem_dest_headquarter_id: Optional[int] = None
    rem_dest_external_lab_id: Optional[int] = None
    rem_observations: Optional[str] = None


class _HeadquarterInfo(BaseModel):
    """Campos adicionales de la sede que se incluyen en la respuesta."""
    name: Optional[str] = None


class _UserInfo(BaseModel):
    """Campos adicionales del usuario que se incluyen en la respuesta."""
    usr_login: Optional[str] = None
    full_name: Optional[str] = None


class RemissionResponse(BaseModel):
    rem_id: int
    rem_consecutive: str
    rem_type: str
    rem_origin_headquarter_id: int
    rem_dest_headquarter_id: Optional[int] = None
    rem_dest_external_lab_id: Optional[int] = None
    rem_state: int
    rem_courier_name: Optional[str] = None
    rem_temperature_courier: Optional[str] = None
    rem_observations: Optional[str] = None
    rem_created_by_user_id: int
    rem_created_at: datetime
    rem_sent_at: Optional[datetime] = None
    rem_received_at: Optional[datetime] = None
    # Campos enriquecidos desde relaciones
    origin_headquarter: Optional[_HeadquarterInfo] = None
    dest_headquarter: Optional[_HeadquarterInfo] = None
    dest_external_lab: Optional[ExternalLabResponse] = None
    created_by_user: Optional[_UserInfo] = None

    class Config:
        from_attributes = True


class RemissionDetailFullResponse(RemissionResponse):
    details: List[RemissionDetailResponse] = []


class RemissionListResponse(BaseModel):
    items: List[RemissionResponse]
    total: int


# ── Ship / Receive Item / Cancel ───────────────────────────────────────

class ShipRemissionRequest(BaseModel):
    rem_courier_name: Optional[str] = None
    rem_temperature_courier: Optional[str] = None


class ReceiveItemRequest(BaseModel):
    remd_id: int
    remd_item_state: int = Field(..., description="2=Recibido Conforme, 3=Rechazado en Destino")
    remd_rejection_reason: Optional[str] = None


class CancelRemissionRequest(BaseModel):
    notes: Optional[str] = None


# ── Generic Message Responses ──────────────────────────────────────────

class MessageResponse(BaseModel):
    success: bool
    message: str


class AddItemsResponse(BaseModel):
    success: bool
    items_count: int
    message: str


class RemissionCreatedResponse(BaseModel):
    success: bool
    rem_id: int
    rem_consecutive: str
    message: str


# ── Órdenes con estudios remitidos / Resultados anexos ─────────────────

class RemittedStudyChild(BaseModel):
    """Un estudio remitido de la orden (JSON hijo)."""
    order_detail_id: int
    study_code: Optional[str] = None
    study_name: Optional[str] = None
    external_lab_id: Optional[int] = None
    external_lab_name: Optional[str] = None
    ar_file_status: str = Field(
        ...,
        description=(
            "'Cargado' o 'Sin resultado Anexo'. Es específico del laboratorio externo "
            "de ESTE estudio: si la orden tiene estudios remitidos a dos laboratorios "
            "distintos, cargar el PDF de uno no cambia el estado del otro."
        ),
    )


class OrderWithRemittedStudiesItem(BaseModel):
    o_id: int
    o_number: Optional[str] = None
    fecha_ingreso: Optional[datetime] = None
    patient_full_name: Optional[str] = None
    pt_number_document: Optional[str] = None
    estudios_remitidos: List[RemittedStudyChild] = []


class OrdersWithRemittedStudiesListResponse(BaseModel):
    items: List[OrderWithRemittedStudiesItem]
    total: int
    skip: int
    limit: int


class UploadRemittedAnnexedResponse(BaseModel):
    success: bool
    ar_id: int
    ar_file: str
    order_id: int
    external_lab_id: int
    external_lab_name: Optional[str] = None
    labs_marked: List[int] = []
    labs_skipped_validated: List[int] = []
    message: str
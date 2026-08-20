from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field, field_serializer, computed_field


# ── Sample States ─────────────────────────────────────────────────────────────
# 0=Recibida  1=En proceso  2=Almacenada  3=Retirada  4=Descartada

# ── SamplesLog ────────────────────────────────────────────────────────────────

class SampleLogCreate(BaseModel):
    barcode: str = Field(..., description="Barcode (so_barcode) of the sample tube")
    log_state: int = Field(..., ge=0, le=4, description="0=Recibida 1=En proceso 2=Almacenada 3=Retirada 4=Descartada")
    log_location_id: Optional[int] = None
    log_observation: Optional[str] = None


class LocationBasic(BaseModel):
    loc_id: int
    loc_name: Optional[str]

    class Config:
        from_attributes = True


class UserBasic(BaseModel):
    usr_id: int
    usr_first_name: Optional[str]
    usr_last_name: Optional[str]

    class Config:
        from_attributes = True


class SampleLogResponse(BaseModel):
    sl_id: int
    log_sample_order_id: Optional[int]
    log_state: Optional[int]
    log_location_id: Optional[int]
    location: Optional[LocationBasic] = None
    log_observation: Optional[str]
    log_user_id: Optional[int]
    user: Optional[UserBasic] = None
    log_create_at: Optional[datetime]
    # Campos enriquecidos
    location_name: Optional[str] = None
    headquarter_name: Optional[str] = None

    @field_serializer("log_create_at")
    def serialize_log_create_at(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return value.strftime("%d/%m/%Y %I:%M %p")

    class Config:
        from_attributes = True


class SampleLogPaginatedResponse(BaseModel):
    items: List[SampleLogResponse]
    total: int
    skip: int
    limit: int


# ── Serotecas ─────────────────────────────────────────────────────────────────

class HeadquarterBasic(BaseModel):
    id: int
    name: Optional[str]

    class Config:
        from_attributes = True


class SerotecaCreate(BaseModel):
    s_name: str
    s_description: Optional[str] = None
    s_location_id: Optional[int] = None
    s_headquarter_id: Optional[int] = None
    s_active: bool = True


class SerotecaUpdate(BaseModel):
    s_name: Optional[str] = None
    s_description: Optional[str] = None
    s_location_id: Optional[int] = None
    s_headquarter_id: Optional[int] = None
    s_active: Optional[bool] = None


class SerotecaResponse(BaseModel):
    s_id: int
    s_name: str
    s_description: Optional[str]
    s_location_id: Optional[int]
    s_headquarter_id: Optional[int] = None
    location: Optional[LocationBasic] = None
    headquarter: Optional[HeadquarterBasic] = None
    s_active: bool
    s_created_at: Optional[datetime]
    s_updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SerotecaPaginatedResponse(BaseModel):
    items: List[SerotecaResponse]
    total: int
    skip: int
    limit: int


# ── Gradillas ─────────────────────────────────────────────────────────────────

class GradillaCreate(BaseModel):
    g_name: str
    g_seroteca_id: int
    g_tipo_gradilla_id: Optional[int] = Field(None, description="ID del tipo de gradilla. Si se provee, rows/cols se heredan del template")
    g_rows: Optional[int] = Field(None, ge=1, le=100)
    g_cols: Optional[int] = Field(None, ge=1, le=100)
    g_created_by: Optional[int] = None


class GradillaUpdate(BaseModel):
    g_name: Optional[str] = None
    g_active: Optional[bool] = None


class PatientBasic(BaseModel):
    pt_id: int
    pt_firts_name: Optional[str]
    pt_middle_name: Optional[str]
    pt_last_name: Optional[str]
    pt_second_last_name: Optional[str]

    @computed_field
    @property
    def full_name(self) -> Optional[str]:
        parts = [
            self.pt_firts_name or "",
            self.pt_middle_name or "",
            self.pt_last_name or "",
            self.pt_second_last_name or "",
        ]
        name = " ".join(p for p in parts if p).strip()
        return name or None

    class Config:
        from_attributes = True


class SampleTypeBasic(BaseModel):
    st_id: int
    st_sufix: Optional[int]

    class Config:
        from_attributes = True


class OrderBasic(BaseModel):
    o_id: int
    o_number: Optional[str]
    o_date: Optional[date] = None
    patient: Optional[PatientBasic] = None

    class Config:
        from_attributes = True


class SampleOrderBasic(BaseModel):
    so_id: int
    so_barcode: Optional[str]
    so_state: Optional[int] = Field(None, description="0=Muestra No Ingresada 1=Con Muestra 2=Muestra Sin Definir 3=Almacenada 4=Descartada")
    order: Optional[OrderBasic] = None
    sample_type: Optional[SampleTypeBasic] = None

    @computed_field
    @property
    def so_state_name(self) -> Optional[str]:
        from app.domains.samples.domain.constants import SAMPLE_ORDER_STATES
        if self.so_state is None:
            return None
        return SAMPLE_ORDER_STATES.get(self.so_state, str(self.so_state))

    @computed_field
    @property
    def is_discarded(self) -> bool:
        from app.domains.samples.domain.constants import SAMPLE_ORDER_STATE_DESCARTADA
        return self.so_state == SAMPLE_ORDER_STATE_DESCARTADA

    @computed_field
    @property
    def order_number_with_suffix(self) -> Optional[str]:
        if self.order and self.sample_type and self.sample_type.st_sufix is not None:
            return f"{self.order.o_number}-{self.sample_type.st_sufix}"
        if self.order:
            return self.order.o_number
        return None

    class Config:
        from_attributes = True


class GradillaPosicionResponse(BaseModel):
    gp_id: int
    gp_gradilla_id: int
    gp_row: int
    gp_col: int
    gp_sample_id: Optional[int]
    gp_occupied: bool
    gp_stored_at: Optional[datetime]
    gp_stored_by_id: Optional[int]
    sample: Optional[SampleOrderBasic] = None

    class Config:
        from_attributes = True


class GradillaResponse(BaseModel):
    g_id: int
    g_name: str
    g_number: Optional[str] = None
    g_seroteca_id: int
    g_rows: int
    g_cols: int
    g_discard_date: Optional[datetime] = None
    g_discarted: int = Field(0, description="0=No descartada, 1=Descartada")
    g_active: bool
    g_created_by: Optional[int]
    g_created_at: Optional[datetime]
    g_updated_at: Optional[datetime]

    @computed_field
    @property
    def days_until_discard(self) -> Optional[int]:
        if self.g_discard_date is None:
            return None
        from utils.timezone import get_bogota_now
        return (self.g_discard_date - get_bogota_now()).days

    @computed_field
    @property
    def about_to_discard(self) -> bool:
        """True solo si a la gradilla le quedan entre 0 y 3 días para su fecha de descarte (y aún no fue descartada)."""
        if self.g_discarted or self.g_discard_date is None:
            return False
        days = self.days_until_discard
        return days is not None and 0 <= days <= 3

    class Config:
        from_attributes = True


class GradillaWithPositionsResponse(GradillaResponse):
    positions: List[GradillaPosicionResponse] = []


class GradillaPaginatedResponse(BaseModel):
    items: List[GradillaResponse]
    total: int
    skip: int
    limit: int


class PendingSampleInfo(BaseModel):
    so_id: int
    so_barcode: Optional[str]
    pending_tests: List[str]
    message: str


class GradillaDiscardResponse(BaseModel):
    g_id: int
    g_name: str
    g_discarted: int = Field(..., description="0=No descartada, 1=Descartada por completo")
    fully_discarded: bool = Field(..., description="True si al terminar no quedó ninguna muestra pendiente en la gradilla")
    samples_discarded: int
    discarded_sample_ids: List[int]
    samples_pending: int
    pending_samples: List[PendingSampleInfo]
    message: str


# ── Tipos de Gradilla ─────────────────────────────────────────────────────────

class TipoGradillaCreate(BaseModel):
    tg_name: str
    tg_rows: int = Field(..., ge=1, le=100)
    tg_cols: int = Field(..., ge=1, le=100)
    tg_storage_days: int = Field(..., ge=1, le=3650, description="Days samples can be stored")


class TipoGradillaUpdate(BaseModel):
    tg_name: Optional[str] = None
    tg_rows: Optional[int] = Field(None, ge=1, le=100)
    tg_cols: Optional[int] = Field(None, ge=1, le=100)
    tg_storage_days: Optional[int] = Field(None, ge=1, le=3650)
    tg_active: Optional[bool] = None


class TipoGradillaResponse(BaseModel):
    tg_id: int
    tg_name: str
    tg_rows: int
    tg_cols: int
    tg_storage_days: int
    tg_active: bool
    tg_created_at: Optional[datetime]
    tg_updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TipoGradillaPaginatedResponse(BaseModel):
    items: List[TipoGradillaResponse]
    total: int
    skip: int
    limit: int


# ── Storage actions ───────────────────────────────────────────────────────────

class AutoStoreRequest(BaseModel):
    barcode: str = Field(..., description="Barcode (so_barcode) of the sample tube")
    g_id: int = Field(..., description="Rack ID to auto-assign sample")


class ManualStoreRequest(BaseModel):
    barcode: str = Field(..., description="Barcode (so_barcode) of the sample tube")

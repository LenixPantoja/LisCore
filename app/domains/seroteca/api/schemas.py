from typing import Optional, List
from datetime import datetime
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

class SerotecaCreate(BaseModel):
    s_name: str
    s_description: Optional[str] = None
    s_location_id: Optional[int] = None
    s_active: bool = True


class SerotecaUpdate(BaseModel):
    s_name: Optional[str] = None
    s_description: Optional[str] = None
    s_location_id: Optional[int] = None
    s_active: Optional[bool] = None


class SerotecaResponse(BaseModel):
    s_id: int
    s_name: str
    s_description: Optional[str]
    s_location_id: Optional[int]
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
    g_rows: int = Field(..., ge=1, le=100)
    g_cols: int = Field(..., ge=1, le=100)
    g_created_by: Optional[int] = None


class GradillaUpdate(BaseModel):
    g_name: Optional[str] = None
    g_active: Optional[bool] = None


class SampleTypeBasic(BaseModel):
    st_id: int
    st_sufix: Optional[int]

    class Config:
        from_attributes = True


class OrderBasic(BaseModel):
    o_id: int
    o_number: Optional[str]

    class Config:
        from_attributes = True


class SampleOrderBasic(BaseModel):
    so_id: int
    so_barcode: Optional[str]
    order: Optional[OrderBasic] = None
    sample_type: Optional[SampleTypeBasic] = None

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
    g_seroteca_id: int
    g_rows: int
    g_cols: int
    g_active: bool
    g_created_by: Optional[int]
    g_created_at: Optional[datetime]
    g_updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class GradillaWithPositionsResponse(GradillaResponse):
    positions: List[GradillaPosicionResponse] = []


class GradillaPaginatedResponse(BaseModel):
    items: List[GradillaResponse]
    total: int
    skip: int
    limit: int


# ── Storage actions ───────────────────────────────────────────────────────────

class AutoStoreRequest(BaseModel):
    barcode: str = Field(..., description="Barcode (so_barcode) of the sample tube")
    g_id: int = Field(..., description="Rack ID to auto-assign sample")


class ManualStoreRequest(BaseModel):
    barcode: str = Field(..., description="Barcode (so_barcode) of the sample tube")

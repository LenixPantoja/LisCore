from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ── Template Element (validación del JSON) ──────────────────────────────────────

class TemplateElement(BaseModel):
    """Un elemento del template (campo dinámico de formulario)."""
    id: str
    name: str
    type: str  # T=Título, Combo=Lista desplegable, Text=Texto, TextArea=Área texto, Radio=RadioButton
    typeName: Optional[str] = None
    row: int = 0
    defaultValue: Optional[str] = ""
    options: List[str] = []
    unit: Optional[str] = ""
    help: Optional[str] = ""
    mask: Optional[str] = ""
    max: Optional[str] = ""
    min: Optional[str] = ""
    loinc: Optional[str] = ""


# ── Wrapper para el JSON exacto que envía el frontend ──────────────────────────

class CompoundTemplatePayload(BaseModel):
    """Wrapper: el frontend envía { template: [...] }."""
    template: List[TemplateElement] = Field(default_factory=list)


# ── CompoundTemplate CRUD ──────────────────────────────────────────────────────

class CompoundTemplateBase(BaseModel):
    ct_name: str = Field(..., min_length=1, max_length=255)
    ct_description: Optional[str] = None
    ct_template: CompoundTemplatePayload = Field(
        default_factory=lambda: CompoundTemplatePayload(template=[]),
        description='JSON con clave "template" que contiene el array de elementos'
    )
    ct_active: Optional[bool] = True


class CompoundTemplateCreate(CompoundTemplateBase):
    pass


class CompoundTemplateUpdate(BaseModel):
    ct_name: Optional[str] = Field(None, min_length=1, max_length=255)
    ct_description: Optional[str] = None
    ct_template: Optional[CompoundTemplatePayload] = None
    ct_active: Optional[bool] = None


class CompoundTemplateResponse(BaseModel):
    ct_id: int
    ct_name: str
    ct_description: Optional[str] = None
    ct_template: Any  # JSONB → dict/list
    ct_active: bool
    ct_created_at: Optional[datetime] = None
    ct_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompoundTemplatePaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[CompoundTemplateResponse]


# ── N:M Link ───────────────────────────────────────────────────────────────────

class TestCompoundTemplateLinkCreate(BaseModel):
    tct_test_id: int
    tct_is_default: Optional[bool] = False
    tct_order_index: Optional[int] = 0


class TestCompoundTemplateLinkUpdate(BaseModel):
    tct_is_default: Optional[bool] = None
    tct_order_index: Optional[int] = None


class TestCompoundTemplateLinkResponse(BaseModel):
    tct_id: int
    tct_test_id: int
    tct_template_id: int
    tct_is_default: bool
    tct_order_index: int
    tct_created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
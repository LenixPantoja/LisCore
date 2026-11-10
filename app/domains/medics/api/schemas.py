from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


def _blank_to_none(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


_OPTIONAL_TEXT = ("med_document_number", "med_specialty", "med_card_professional_number", "med_phone", "med_mail", "med_user")


class MedicBase(BaseModel):
    med_codigo: str = Field(..., min_length=1, max_length=30, description="Código del médico (único)")
    med_name: str = Field(..., min_length=3, max_length=200)
    med_document_number: Optional[str] = Field(None, max_length=30)
    med_specialty: Optional[str] = Field(None, max_length=150)
    med_card_professional_number: Optional[str] = Field(None, max_length=50)
    med_phone: Optional[str] = Field(None, max_length=50)
    med_mail: Optional[EmailStr] = None
    med_user: Optional[str] = Field(None, max_length=100)
    med_reset_password: bool = False
    med_is_locked: bool = False
    med_is_active: bool = True

    @field_validator(*_OPTIONAL_TEXT, mode="before")
    @classmethod
    def _strip(cls, v):
        return _blank_to_none(v)

    @field_validator("med_codigo", mode="before")
    @classmethod
    def _codigo(cls, v):
        return v.strip().upper() if isinstance(v, str) else (str(v) if v is not None else v)

    @field_validator("med_name", mode="before")
    @classmethod
    def _name(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


class MedicCreate(MedicBase):
    # Contraseña en texto plano: se guarda como hash bcrypt
    med_password: Optional[str] = Field(None, min_length=6, max_length=100)

    @field_validator("med_password", mode="before")
    @classmethod
    def _pwd(cls, v):
        return _blank_to_none(v)


class MedicUpdate(BaseModel):
    med_codigo: Optional[str] = Field(None, min_length=1, max_length=30)
    med_name: Optional[str] = Field(None, min_length=3, max_length=200)
    med_document_number: Optional[str] = Field(None, max_length=30)
    med_specialty: Optional[str] = Field(None, max_length=150)
    med_card_professional_number: Optional[str] = Field(None, max_length=50)
    med_phone: Optional[str] = Field(None, max_length=50)
    med_mail: Optional[EmailStr] = None
    med_user: Optional[str] = Field(None, max_length=100)
    # Si se envía con valor, reemplaza la contraseña; vacío = no se cambia
    med_password: Optional[str] = Field(None, min_length=6, max_length=100)
    med_reset_password: Optional[bool] = None
    med_is_locked: Optional[bool] = None
    med_is_active: Optional[bool] = None

    @field_validator(*_OPTIONAL_TEXT, "med_password", mode="before")
    @classmethod
    def _strip(cls, v):
        return _blank_to_none(v)

    @field_validator("med_codigo", mode="before")
    @classmethod
    def _codigo(cls, v):
        if isinstance(v, str):
            v = v.strip().upper()
            return v or None
        return str(v) if v is not None else v

    @field_validator("med_name", mode="before")
    @classmethod
    def _name(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


class MedicResponse(BaseModel):
    """Médico sin la contraseña."""
    med_id: int
    med_codigo: str
    med_name: str
    med_document_number: Optional[str] = None
    med_specialty: Optional[str] = None
    med_card_professional_number: Optional[str] = None
    med_phone: Optional[str] = None
    med_mail: Optional[str] = None
    med_user: Optional[str] = None
    med_has_password: bool = False
    med_reset_password: bool
    med_is_locked: bool
    med_is_active: bool
    med_created_at: Optional[datetime] = None
    med_updated_at: Optional[datetime] = None


class MedicPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[MedicResponse]


class MedicOption(BaseModel):
    """Opción para el selector de médico al crear una orden."""
    med_id: int
    med_codigo: str
    med_name: str
    med_document_number: Optional[str] = None
    med_specialty: Optional[str] = None
    med_card_professional_number: Optional[str] = None

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Channel = Literal["LLAMADA", "WHATSAPP", "CORREO", "PRESENCIAL"]
Gender = Literal["AMBOS", "MASCULINO", "FEMENINO"]
AgeType = Literal["DIAS", "MESES", "AÑOS"]
Pregnancy = Literal["TODAS", "EMBARAZADA", "NO_EMBARAZADA"]


def _strip(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


class NotifyRequest(BaseModel):
    channel: Channel
    contact: str = Field(..., min_length=3, max_length=255, description="A quién se notificó (nombre y cargo)")
    read_back: bool = Field(False, description="El médico repitió el resultado y el nombre del paciente")
    note: Optional[str] = Field(None, max_length=1000)

    @field_validator("contact", "note", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return _strip(v)


class NoteRequest(BaseModel):
    note: str = Field(..., min_length=3, max_length=1000)

    @field_validator("note", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return _strip(v)


class AcknowledgeRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=1000)


class CloseRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000, description="Conducta tomada o motivo de cierre")
    without_notification: bool = Field(False, description="Cerrar sin notificar: el resultado no es válido")

    @field_validator("reason", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return _strip(v)


class RuleBase(BaseModel):
    gender: Gender = "AMBOS"
    age_type: AgeType = "AÑOS"
    min_age: Optional[int] = Field(None, ge=0, le=150)
    max_age: Optional[int] = Field(None, ge=0, le=150)
    panic_low: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    panic_high: Optional[float] = None
    delta_pct: Optional[float] = Field(None, gt=0, le=1000)
    delta_days: int = Field(30, ge=1, le=3650)
    notify_minutes: int = Field(30, ge=1, le=1440)
    block_validation: bool = False
    active: bool = True
    note: Optional[str] = Field(None, max_length=1000)
    msg_panic_low: Optional[str] = Field(None, max_length=255, description="Posible patología si es menor que pánico bajo")
    msg_critical_low: Optional[str] = Field(None, max_length=255)
    msg_critical_high: Optional[str] = Field(None, max_length=255)
    msg_panic_high: Optional[str] = Field(None, max_length=255)
    msg_delta: Optional[str] = Field(None, max_length=255)
    pregnancy: Optional[Pregnancy] = Field(None, description="TODAS | EMBARAZADA | NO_EMBARAZADA")
    min_week: Optional[int] = Field(None, ge=0, le=45, description="Semana de gestación desde (solo EMBARAZADA)")
    max_week: Optional[int] = Field(None, ge=0, le=45)
    enterprise_id: Optional[int] = Field(None, description="Solo órdenes de esta empresa (vacío = todas)")

    @field_validator("note", "msg_panic_low", "msg_critical_low", "msg_critical_high", "msg_panic_high", "msg_delta", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return _strip(v)


class RuleCreate(RuleBase):
    test_id: int


class RuleUpdate(BaseModel):
    gender: Optional[Gender] = None
    age_type: Optional[AgeType] = None
    min_age: Optional[int] = Field(None, ge=0, le=150)
    max_age: Optional[int] = Field(None, ge=0, le=150)
    panic_low: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    panic_high: Optional[float] = None
    delta_pct: Optional[float] = Field(None, gt=0, le=1000)
    delta_days: Optional[int] = Field(None, ge=1, le=3650)
    notify_minutes: Optional[int] = Field(None, ge=1, le=1440)
    block_validation: Optional[bool] = None
    active: Optional[bool] = None
    note: Optional[str] = Field(None, max_length=1000)
    msg_panic_low: Optional[str] = Field(None, max_length=255, description="Posible patología si es menor que pánico bajo")
    msg_critical_low: Optional[str] = Field(None, max_length=255)
    msg_critical_high: Optional[str] = Field(None, max_length=255)
    msg_panic_high: Optional[str] = Field(None, max_length=255)
    msg_delta: Optional[str] = Field(None, max_length=255)
    pregnancy: Optional[Pregnancy] = Field(None, description="TODAS | EMBARAZADA | NO_EMBARAZADA")
    min_week: Optional[int] = Field(None, ge=0, le=45, description="Semana de gestación desde (solo EMBARAZADA)")
    max_week: Optional[int] = Field(None, ge=0, le=45)
    enterprise_id: Optional[int] = Field(None, description="Solo órdenes de esta empresa (vacío = todas)")

    @field_validator("note", "msg_panic_low", "msg_critical_low", "msg_critical_high", "msg_panic_high", "msg_delta", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return _strip(v)

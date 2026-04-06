from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

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

class OrderCreate(OrderBase):
    """Esquema para crear una orden con sus estudios solicitados."""
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

    class Config:
        from_attributes = True
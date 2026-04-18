from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, List, Any
from datetime import date, datetime
from app.domains.patients.api.schemas import PatientResponse
from app.domains.testslabs.api.schemas import TestsLabResponse
from app.domains.studieslab.api.schemas import StudiesLabResponse
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

    class Config:
        from_attributes = True

class OrderPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[OrderResponse]

class NextOrderNumberResponse(BaseModel):
    next_order_number: str

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
    od_state: Optional[int] = None
    study: Optional[BasicStudiesLabResponse] = None

    class Config:
        from_attributes = True

class LaboratoryResponse(BaseModel):
    l_id: int
    l_order_detail_id: Optional[int] = None
    l_test_id: Optional[int] = None
    l_result: Optional[str] = None
    l_result_num: Optional[float] = None
    l_result_comp: Optional[str] = None
    l_result_graphic: Optional[str] = None
    l_nota_validation: Optional[str] = None
    l_state: Optional[int] = None
    l_date_transmited: Optional[datetime] = None
    l_date_validatie: Optional[datetime] = None
    l_user_validation_id: Optional[int] = None
    a_analyzer_result_id: Optional[int] = None
    l_created_at: datetime
    l_updated_at: datetime
    
    order_detail: Optional[BasicOrdersDetailResponse] = None
    test: Optional[TestsLabResponse] = None
    user_validation: Optional[UserValidationResponse] = None

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

class OrderFullDetailsResponse(BaseModel):
    order: OrderResponse
    patient: PatientResponse
    laboratories: List[LaboratoryResponse]
    tests: List[TestsLabResponse]

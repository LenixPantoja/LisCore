from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime

class PatientBase(BaseModel):
    pt_Number_document: str
    pt_firts_name: str
    pt_middle_name: Optional[str] = None
    pt_last_name: str
    pt_second_last_name: str
    pt_sex_type: Optional[int] = None
    pt_phone_number: Optional[str] = None
    pt_mail: Optional[EmailStr] = None
    pt_address: Optional[str] = None
    pt_date_of_birth: Optional[date] = None
    pt_authorize_habeas_data: Optional[bool] = False
    pt_afiliation_type: Optional[int] = None
    pt_enterprise_id: Optional[int] = None
    pt_Document_Type_id: Optional[int] = None
    pt_city_id: Optional[int] = None

class PatientCreate(PatientBase):
    pt_password: Optional[str] = None

class PatientUpdate(BaseModel):
    pt_firts_name: Optional[str] = None
    pt_middle_name: Optional[str] = None
    pt_last_name: Optional[str] = None
    pt_second_last_name: Optional[str] = None
    pt_phone_number: Optional[str] = None
    pt_mail: Optional[EmailStr] = None
    pt_address: Optional[str] = None
    pt_authorize_habeas_data: Optional[bool] = None
    pt_enterprise_id: Optional[int] = None
    pt_city_id: Optional[int] = None
    pt_password: Optional[str] = None

class PatientResponse(PatientBase):
    pt_id: int
    pt_created_at: datetime
    pt_updated_at: datetime

    class Config:
        from_attributes = True

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# --- Interfaces Rest ---

class InterfacesRestBase(BaseModel):
    it_enterprise_id: Optional[int] = None
    it_tariff_id: Optional[int] = None
    it_state: Optional[bool] = True

class InterfacesRestCreate(InterfacesRestBase):
    pass

class InterfacesRestUpdate(BaseModel):
    it_enterprise_id: Optional[int] = None
    it_tariff_id: Optional[int] = None
    it_state: Optional[bool] = None

class EnterpriseSimpleInfo(BaseModel):
    en_id: int
    en_name: Optional[str] = None

    class Config:
        from_attributes = True

class TariffSimpleInfo(BaseModel):
    t_id: int
    t_name: Optional[str] = None

    class Config:
        from_attributes = True

class InterfacesRestResponse(InterfacesRestBase):
    it_id: int
    it_created_at: Optional[datetime] = None
    it_updated_at: Optional[datetime] = None
    enterprise: Optional[EnterpriseSimpleInfo] = None
    tariff: Optional[TariffSimpleInfo] = None

    class Config:
        from_attributes = True

class InterfacesRestPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[InterfacesRestResponse]


# --- Interfaces Rest Details ---

class InterfacesRestDetailBase(BaseModel):
    itd_interface_rest_id: int
    itd_study_id: Optional[int] = None
    itd_send_code: Optional[str] = None
    itd_receipt_code: Optional[str] = None

class InterfacesRestDetailCreate(InterfacesRestDetailBase):
    pass

class InterfacesRestDetailUpdate(BaseModel):
    itd_study_id: Optional[int] = None
    itd_send_code: Optional[str] = None
    itd_receipt_code: Optional[str] = None

class StudySimpleInfo(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None

    class Config:
        from_attributes = True

class InterfacesRestDetailResponse(InterfacesRestDetailBase):
    itd_id: int
    itd_created_at: Optional[datetime] = None
    itd_updated_at: Optional[datetime] = None
    study: Optional[StudySimpleInfo] = None

    class Config:
        from_attributes = True

class InterfacesRestDetailPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[InterfacesRestDetailResponse]

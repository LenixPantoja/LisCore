from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class EnterpriseBase(BaseModel):
    en_code: Optional[str] = None
    en_name: Optional[str] = None
    en_description: Optional[str] = None
    en_nit: Optional[str] = None
    en_div: Optional[str] = None
    en_address: Optional[str] = None
    en_phone: Optional[str] = None
    en_Legal_representative: Optional[str] = None
    en_mail: Optional[EmailStr] = None
    en_observations: Optional[str] = None
    en_active: Optional[bool] = True
    en_send_mail: Optional[bool] = False
    en_send_whatsapp: Optional[bool] = False
    en_alternative_contact: Optional[str] = None
    en_email_electronic_invoice: Optional[EmailStr] = None
    en_regimen_id: Optional[int] = None
    en_classification_id: Optional[int] = None
    en_document_type_id: Optional[int] = None
    en_city_id: Optional[int] = None
    en_liability_type_id: Optional[int] = None
    en_type_organization_id: Optional[int] = None
    en_password: Optional[str] = None

class EnterpriseCreate(EnterpriseBase):
    """Schema for creating a new enterprise."""
    pass

class EnterpriseUpdate(BaseModel):
    """Schema for updating an existing enterprise."""
    en_code: Optional[str] = None
    en_name: Optional[str] = None
    en_description: Optional[str] = None
    en_nit: Optional[str] = None
    en_div: Optional[str] = None
    en_address: Optional[str] = None
    en_phone: Optional[str] = None
    en_Legal_representative: Optional[str] = None
    en_mail: Optional[EmailStr] = None
    en_observations: Optional[str] = None
    en_active: Optional[bool] = None
    en_send_mail: Optional[bool] = None
    en_send_whatsapp: Optional[bool] = None
    en_alternative_contact: Optional[str] = None
    en_email_electronic_invoice: Optional[EmailStr] = None
    en_regimen_id: Optional[int] = None
    en_classification_id: Optional[int] = None
    en_document_type_id: Optional[int] = None
    en_city_id: Optional[int] = None
    en_liability_type_id: Optional[int] = None
    en_type_organization_id: Optional[int] = None
    en_password: Optional[str] = None

class EnterpriseResponse(EnterpriseBase):
    """Schema for returning enterprise data."""
    en_id: int
    en_created_at: datetime
    en_updated_at: datetime

    class Config:
        from_attributes = True # Enables ORM mode for Pydantic v2+

class EnterprisePaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[EnterpriseResponse]
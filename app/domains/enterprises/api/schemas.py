from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date

# ── Nested schemas ────────────────────────────────────────────────────────────

class RegimenSchema(BaseModel):
    re_id: int
    re_name: Optional[str] = None
    re_dian_code: Optional[int] = None

    class Config:
        from_attributes = True

class ClassificationSchema(BaseModel):
    cl_id: int
    cl_code: Optional[str] = None
    cl_name: Optional[str] = None

    class Config:
        from_attributes = True

class DocumentTypeSchema(BaseModel):
    dt_id: int
    dt_code: Optional[str] = None
    dt_name: Optional[str] = None

    class Config:
        from_attributes = True

class CitySchema(BaseModel):
    id: int
    city_code: Optional[str] = None
    city_name: Optional[str] = None
    postal_code: Optional[str] = None

    class Config:
        from_attributes = True

class TypeLiabilitySchema(BaseModel):
    id: int
    dian_code_liability: Optional[str] = None
    name: Optional[str] = None

    class Config:
        from_attributes = True

# ── Enterprise schemas ────────────────────────────────────────────────────────

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
    """Schema for returning enterprise data, including related entities."""
    en_id: int
    en_created_at: datetime
    en_updated_at: datetime

    regimen: Optional[RegimenSchema] = None
    classification: Optional[ClassificationSchema] = None
    document_type: Optional[DocumentTypeSchema] = None
    city: Optional[CitySchema] = None
    liability_type: Optional[TypeLiabilitySchema] = None

    class Config:
        from_attributes = True

class EnterprisePaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[EnterpriseResponse]

# ── Enterprise contracts schemas ──────────────────────────────────────────────

class TariffInContractSchema(BaseModel):
    t_id: int
    t_name: Optional[str] = None
    t_description: Optional[str] = None
    t_activo: Optional[bool] = None

    class Config:
        from_attributes = True

class ContractTariffLinkSchema(BaseModel):
    ct_id: int
    ct_active: Optional[bool] = None
    ct_start_date: Optional[date] = None
    ct_end_date: Optional[date] = None
    tariff: Optional[TariffInContractSchema] = None

    class Config:
        from_attributes = True

class EnterpriseContractSchema(BaseModel):
    co_id: int
    co_code: Optional[str] = None
    co_contract_number: Optional[str] = None
    co_number_poliza: Optional[str] = None
    co_observations: Optional[str] = None
    co_value_contracted: Optional[float] = None
    co_value_consumed: Optional[float] = None
    co_value_alarm: Optional[float] = None
    co_billing_type: Optional[int] = None
    co_active: Optional[bool] = None
    co_created_at: Optional[date] = None
    co_updated_at: Optional[date] = None
    tariffs_link: List[ContractTariffLinkSchema] = []

    class Config:
        from_attributes = True

class EnterpriseContractsPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[EnterpriseContractSchema]
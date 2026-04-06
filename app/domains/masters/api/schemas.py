from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class CountryBase(BaseModel):
    code_country: str
    name_country: str
    country_active: bool

class CountryResponse(CountryBase):
    id: int

    class Config:
        from_attributes = True

# --- Diagnoses ---
class DiagnosisResponse(BaseModel):
    diag_id: int
    diag_code: Optional[str] = None
    d_description: Optional[str] = None
    diag_created_at: Optional[datetime] = None
    diag_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Schooling ---
class SchoolingResponse(BaseModel):
    id: int
    code: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True

# --- Techniques ---
class TechniqueBase(BaseModel):
    name: str

class TechniqueCreate(TechniqueBase):
    pass

class TechniqueUpdate(BaseModel):
    name: Optional[str] = None

class TechniqueResponse(TechniqueBase):
    id: int
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    class Config:
        from_attributes = True

# --- Work Groups ---
class WorkGroupBase(BaseModel):
    wg_code: str
    wg_name: str
    wg_order_of_print: Optional[int] = None

class WorkGroupCreate(WorkGroupBase):
    pass

class WorkGroupUpdate(BaseModel):
    wg_code: Optional[str] = None
    wg_name: Optional[str] = None
    wg_order_of_print: Optional[int] = None

class WorkGroupResponse(WorkGroupBase):
    wg_id: int
    class Config:
        from_attributes = True

# --- Referral Locations ---
class ReferralLocationBase(BaseModel):
    name: str
    description: Optional[str] = None
    active: Optional[bool] = True

class ReferralLocationCreate(ReferralLocationBase):
    pass

class ReferralLocationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

class ReferralLocationResponse(ReferralLocationBase):
    id: int
    created_at: Optional[date] = None
    update_at: Optional[date] = None
    class Config:
        from_attributes = True

class DepartmentBase(BaseModel):
    d_country_id: int
    d_code: str
    d_name_department: str

class DepartmentResponse(DepartmentBase):
    d_id: int

    class Config:
        from_attributes = True

class CityResponse(BaseModel):
    id: int
    Department_id: int
    city_code: str
    city_name: str
    postal_code: Optional[str] = None

    class Config:
        from_attributes = True

class DocumentTypeResponse(BaseModel):
    dt_id: int
    dt_code: Optional[str] = None
    dt_name: Optional[str] = None

    class Config:
        from_attributes = True

class SexTypeResponse(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True

class AfiliationTypeResponse(BaseModel):
    id: int
    af_name: Optional[str] = None

    class Config:
        from_attributes = True

class RegimeResponse(BaseModel):
    re_id: int
    re_name: Optional[str] = None
    re_dian_code: Optional[int] = None

    class Config:
        from_attributes = True

class ServiceResponse(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None

    class Config:
        from_attributes = True

class TypeLiabilityResponse(BaseModel):
    id: int
    dian_code_liability: Optional[str] = None
    name: Optional[str] = None

    class Config:
        from_attributes = True

class ClassificationResponse(BaseModel):
    cl_id: int
    cl_code: Optional[str] = None
    cl_name: Optional[str] = None

    class Config:
        from_attributes = True
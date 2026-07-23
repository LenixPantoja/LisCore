from datetime import date
from typing import List, Optional

from pydantic import BaseModel


# --- Login ---

class PortalLoginRequest(BaseModel):
    login: str
    password: str


class PortalPatientData(BaseModel):
    pt_id: int
    document_number: str
    fullname: str
    mail: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None


class PortalEnterpriseData(BaseModel):
    en_id: int
    nit: str
    name: str
    mail: Optional[str] = None


class PortalLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    arp_user_access_type: int
    patient: Optional[PortalPatientData] = None
    enterprise: Optional[PortalEnterpriseData] = None


class PortalChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    detail: str


# --- Resultados ---

class ReferenceValueItem(BaseModel):
    min_value: Optional[float] = None
    max_values: Optional[float] = None
    text_value: Optional[str] = None


class ReferenceRangeItem(BaseModel):
    range_type: Optional[str] = None
    gender: Optional[str] = None
    age_type: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    priority: Optional[int] = None
    values: List[ReferenceValueItem] = []


class StudyResultItem(BaseModel):
    test_name: str
    result: Optional[str] = None
    units: Optional[str] = None
    l_state: str
    l_date_validatie: Optional[str] = None  # formato dd-mm-aaaa hh:mm AM/PM
    is_required: bool = False
    reference_ranges: List[ReferenceRangeItem] = []
    alternative_range_value: Optional[str] = None


class StudyWithResults(BaseModel):
    study_name: str
    results: List[StudyResultItem] = []


class PatientOrderItem(BaseModel):
    o_id: int
    o_number: Optional[str] = None
    o_autorizacion: str = ""
    document_number: Optional[str] = None
    fullname_patient: str
    o_date: Optional[date] = None
    o_order_state: str
    studies: List[StudyWithResults] = []


class PatientOrdersPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[PatientOrderItem]


class EnterpriseOrderItem(BaseModel):
    o_id: int
    o_number: Optional[str] = None
    io_number_request: str = ""
    document_number: Optional[str] = None
    fullname_patient: str
    o_date: Optional[date] = None
    age: Optional[str] = None
    sex: Optional[str] = None
    o_order_state: str
    studies: List[StudyWithResults] = []


class EnterpriseOrdersPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[EnterpriseOrderItem]

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

class TariffDetailBase(BaseModel):
    td_studie_id: int
    td_value: float

class TariffDetailResponse(TariffDetailBase):
    td_id: int
    td_tariff_id: int

    class Config:
        from_attributes = True

class StudieInfo(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None

    class Config:
        from_attributes = True

class StudieWithTariffValueResponse(BaseModel):
    """Study info with its tariff detail value"""
    id: int
    code: Optional[str] = None
    cups_code: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None
    order_of_print: Optional[int] = None
    referral_location_id: Optional[int] = None
    work_groups_id: Optional[int] = None
    td_value: float
    td_id: int

    class Config:
        from_attributes = True

class EnterpriseTariffStudiesResponse(BaseModel):
    enterprise_id: int
    tariff_id: int
    tariff_name: Optional[str] = None
    total: int
    skip: int
    limit: int
    items: List[StudieWithTariffValueResponse]

class TariffDetailUpdate(BaseModel):
    td_studie_id: Optional[int] = None
    td_value: Optional[float] = None

class TariffDetailWithStudieResponse(TariffDetailBase):
    td_id: int
    td_tariff_id: int
    studie: Optional[StudieInfo] = None

    class Config:
        from_attributes = True

class TariffDetailPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[TariffDetailWithStudieResponse]

class TariffBase(BaseModel):
    t_name: str
    t_description: Optional[str] = None
    t_activo: Optional[bool] = True

class TariffCreate(TariffBase):
    details: Optional[List[TariffDetailBase]] = []

class TariffUpdate(BaseModel):
    t_name: Optional[str] = None
    t_description: Optional[str] = None
    t_activo: Optional[bool] = None

class TariffResponse(TariffBase):
    t_id: int
    t_created_at: Optional[date] = None
    t_update_at: Optional[date] = None
    details: Optional[List[TariffDetailResponse]] = []

    class Config:
        from_attributes = True

class TariffPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[TariffResponse]

class ContractBase(BaseModel):
    co_code: Optional[str] = None
    co_observations: Optional[str] = None
    co_value_contracted: Optional[float] = None
    co_value_consumed: Optional[float] = None
    co_value_alarm: Optional[float] = None
    co_billing_type: Optional[int] = None
    co_contract_number: Optional[str] = None
    co_number_poliza: Optional[str] = None
    co_active: Optional[bool] = True
    co_enterprise_id: Optional[int] = None

class ContractCreate(ContractBase):
    pass

class ContractUpdate(ContractBase):
    pass

class EnterpriseInfo(BaseModel):
    en_id: int
    en_code: Optional[str] = None
    en_name: Optional[str] = None

    class Config:
        from_attributes = True

class ContractResponse(ContractBase):
    co_id: int
    co_created_at: Optional[date] = None
    co_updated_at: Optional[date] = None
    enterprise: Optional[EnterpriseInfo] = None

    class Config:
        from_attributes = True

class ContractPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[ContractResponse]

# --- Link Tariff to Contract ---

class LinkTariffToContractRequest(BaseModel):
    ct_contract_id: int
    ct_tariff_id: int
    ct_active: Optional[bool] = True
    ct_start_date: Optional[date] = None
    ct_end_date: Optional[date] = None

class ContractTariffResponse(BaseModel):
    ct_id: int
    ct_contract_id: int
    ct_tariff_id: int
    ct_active: Optional[bool] = True
    ct_start_date: Optional[date] = None
    ct_end_date: Optional[date] = None

    class Config:
        from_attributes = True

class UnlinkTariffFromContractRequest(BaseModel):
    ct_contract_id: int
    ct_tariff_id: int

class UnlinkTariffFromContractResponse(BaseModel):
    success: bool
    message: str
    ct_id: Optional[int] = None
    ct_contract_id: Optional[int] = None
    ct_tariff_id: Optional[int] = None

# --- Enterprise contracts listing ---

class TariffInContractResponse(BaseModel):
    """Tariff summary as linked to a contract, including link metadata."""
    t_id: int
    t_name: Optional[str] = None
    t_description: Optional[str] = None
    t_activo: Optional[bool] = None
    ct_id: int
    ct_active: Optional[bool] = None
    ct_start_date: Optional[date] = None
    ct_end_date: Optional[date] = None

    class Config:
        from_attributes = True

class ContractWithTariffsResponse(ContractBase):
    """Contract with its linked tariffs."""
    co_id: int
    co_created_at: Optional[date] = None
    co_updated_at: Optional[date] = None
    enterprise: Optional[EnterpriseInfo] = None
    tariffs: List[TariffInContractResponse] = []

    class Config:
        from_attributes = True

class EnterpriseContractsPaginatedResponse(BaseModel):
    enterprise_id: int
    total: int
    skip: int
    limit: int
    items: List[ContractWithTariffsResponse]

# --- Contract tariffs listing (paginated) ---

class ContractTariffsPaginatedResponse(BaseModel):
    contract_id: int
    total: int
    skip: int
    limit: int
    items: List[TariffResponse]
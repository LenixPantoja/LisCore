from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from decimal import Decimal

# --- Tarifas ---
class TariffDetailBase(BaseModel):
    td_studie_id: int
    td_value: Decimal

class TariffDetailCreate(TariffDetailBase):
    pass

class TariffDetailResponse(TariffDetailBase):
    td_id: int
    td_tariff_id: int
    class Config:
        from_attributes = True

class TariffBase(BaseModel):
    t_name: str
    t_description: Optional[str] = None
    t_activo: Optional[bool] = True

class TariffCreate(TariffBase):
    pass

class TariffResponse(TariffBase):
    t_id: int
    t_created_at: Optional[date] = None
    t_update_at: Optional[date] = None
    details: List[TariffDetailResponse] = []
    class Config:
        from_attributes = True

# --- Contratos ---
class ContractBase(BaseModel):
    co_code: str
    co_observations: Optional[str] = None
    co_value_contracted: Optional[Decimal] = None
    co_value_consumed: Optional[Decimal] = None
    co_value_alarm: Optional[Decimal] = None
    co_billing_type: Optional[int] = None
    co_contract_number: Optional[str] = None
    co_number_poliza: Optional[str] = None
    co_active: Optional[bool] = True
    co_enterprise_id: int

class ContractCreate(ContractBase):
    pass

class ContractResponse(ContractBase):
    co_id: int
    co_created_at: Optional[date] = None
    co_updated_at: Optional[date] = None
    class Config:
        from_attributes = True

# --- Relación Contrato-Tarifa ---
class ContractTariffBase(BaseModel):
    ct_contract_id: int
    ct_tariff_id: int
    ct_active: Optional[bool] = True
    ct_start_date: Optional[date] = None
    ct_end_date: Optional[date] = None

class ContractTariffCreate(ContractTariffBase):
    pass

class ContractTariffResponse(ContractTariffBase):
    ct_id: int
    tariff: Optional[TariffResponse] = None
    class Config:
        from_attributes = True
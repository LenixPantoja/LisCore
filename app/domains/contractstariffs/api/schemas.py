from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ContractBase(BaseModel):
    co_code: str
    co_enterprise_id: int
    co_active: bool
    co_value_contracted: float
    co_value_consumed: float
    co_contract_number: str
    co_number_poliza:  str
    
    
    co_active: Optional[bool] = True

class ContractResponse(ContractBase):
    co_id: int
    co_created_at: Optional[datetime] = None
    co_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ContractPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[ContractResponse]
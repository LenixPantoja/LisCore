from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HeadquarterBase(BaseModel):
    name: str
    resolution: Optional[str] = None
    prefix: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    City: Optional[int] = None
    active: Optional[bool] = True

class HeadquarterCreate(HeadquarterBase):
    pass

class HeadquarterUpdate(BaseModel):
    name: Optional[str] = None
    resolution: Optional[str] = None
    prefix: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    City: Optional[int] = None
    active: Optional[bool] = None

class HeadquarterResponse(HeadquarterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
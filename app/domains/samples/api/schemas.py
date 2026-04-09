from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SampleTypeBase(BaseModel):
    st_name: str
    st_color: Optional[str] = None
    st_sufix: Optional[int] = None
    st_type_temp: Optional[str] = None
    st_active: Optional[bool] = True

class SampleTypeCreate(SampleTypeBase):
    pass

class SampleTypeUpdate(BaseModel):
    st_name: Optional[str] = None
    st_color: Optional[str] = None
    st_sufix: Optional[int] = None
    st_type_temp: Optional[str] = None
    st_active: Optional[bool] = None

class SampleTypeResponse(SampleTypeBase):
    st_id: int

    class Config:
        from_attributes = True

class SampleTypePaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[SampleTypeResponse]
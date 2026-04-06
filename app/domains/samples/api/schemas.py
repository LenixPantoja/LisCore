from pydantic import BaseModel
from typing import Optional

class SampleTypeBase(BaseModel):
    st_name: str
    st_color: Optional[str] = None
    st_sufix: Optional[int] = None
    st_type_temp: Optional[str] = None
    st_active: Optional[bool] = True

class SampleTypeCreate(SampleTypeBase):
    """Esquema para crear un tipo de muestra."""
    pass

class SampleTypeUpdate(BaseModel):
    """Esquema para actualizar un tipo de muestra."""
    st_name: Optional[str] = None
    st_color: Optional[str] = None
    st_sufix: Optional[int] = None
    st_type_temp: Optional[str] = None
    st_active: Optional[bool] = None

class SampleTypeResponse(SampleTypeBase):
    st_id: int

    class Config:
        from_attributes = True
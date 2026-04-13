from pydantic import BaseModel
from typing import Optional, List

class CityResponse(BaseModel):
    id: int
    Department_id: int
    city_code: str
    city_name: str
    postal_code: Optional[str] = None

    class Config:
        from_attributes = True

class CityPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[CityResponse]

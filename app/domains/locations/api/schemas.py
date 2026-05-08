from pydantic import BaseModel
from typing import Optional, List

class LocationResponse(BaseModel):
    loc_id: int
    loc_name: Optional[str] = None
    loc_active: Optional[bool] = True

    class Config:
        from_attributes = True

class LocationPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[LocationResponse]

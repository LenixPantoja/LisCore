from pydantic import BaseModel
from typing import Optional, List

# --- Studies Lab ---
class StudiesLabBase(BaseModel):
    code: str
    cups_code: Optional[str] = None
    name: str
    order_of_print: Optional[int] = None
    referral_location_id: Optional[int] = None
    work_groups_id: Optional[int] = None
    active: Optional[bool] = True

class StudiesLabCreate(StudiesLabBase):
    pass

class StudiesLabUpdate(BaseModel):
    code: Optional[str] = None
    cups_code: Optional[str] = None
    name: Optional[str] = None
    order_of_print: Optional[int] = None
    referral_location_id: Optional[int] = None
    work_groups_id: Optional[int] = None
    active: Optional[bool] = None

# --- Studies Test Detail ---
class StudiesTestDetailBase(BaseModel):
    tests_id: int
    order_print: Optional[int] = 0
    is_required: Optional[bool] = False
    work_group_id: Optional[int] = None

class StudiesTestDetailCreate(StudiesTestDetailBase):
    pass

class StudiesTestDetailResponse(StudiesTestDetailBase):
    id: int
    studies_id: int

    class Config:
        from_attributes = True

# --- Combined Response ---
class StudiesLabResponse(StudiesLabBase):
    id: int
    test_details: List[StudiesTestDetailResponse] = []

    class Config:
        from_attributes = True
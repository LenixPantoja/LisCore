from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FormatCompleteBase(BaseModel):
    fc_name: str
    fc_description: Optional[str] = None
    fc_active: Optional[bool] = True


class FormatCompleteCreate(FormatCompleteBase):
    pass


class FormatCompleteUpdate(BaseModel):
    fc_name: Optional[str] = None
    fc_description: Optional[str] = None
    fc_active: Optional[bool] = None


class FormatCompleteResponse(FormatCompleteBase):
    fc_id: int
    fc_created_at: Optional[datetime] = None
    fc_updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FormatCompleteListResponse(BaseModel):
    total: int
    items: List[FormatCompleteResponse]


# --- Testslab ↔ FormatComplete (relación) ---

class TestslabFormatCompleteCreate(BaseModel):
    tfc_format_complete_id: int
    tfc_is_default: Optional[bool] = False
    tfc_order_index: Optional[int] = 0


class TestslabFormatCompleteUpdate(BaseModel):
    tfc_is_default: Optional[bool] = None
    tfc_order_index: Optional[int] = None


class TestslabFormatCompleteResponse(BaseModel):
    tfc_id: int
    tfc_testslab_id: int
    tfc_format_complete_id: int
    tfc_is_default: bool
    tfc_order_index: int
    tfc_created_at: Optional[datetime] = None
    format_complete: Optional[FormatCompleteResponse] = None

    model_config = {"from_attributes": True}


class TestslabFormatCompleteListResponse(BaseModel):
    total: int
    items: List[TestslabFormatCompleteResponse]

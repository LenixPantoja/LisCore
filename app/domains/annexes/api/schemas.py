from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AnnexedResultUploadRequest(BaseModel):
    order_id: int
    user_id: Optional[int] = None


class AnnexedResultResponse(BaseModel):
    ar_id: int
    ar_order_id: int
    ar_file: str
    ar_user_record_file: Optional[int] = None
    ar_created_at: datetime
    ar_updated_at: datetime

    class Config:
        from_attributes = True


class AnnexedResultUploadResponse(BaseModel):
    success: bool
    ar_id: int
    ar_file: str
    order_id: int
    message: str


class AnnexedResultListResponse(BaseModel):
    items: List[AnnexedResultResponse]
    total: int
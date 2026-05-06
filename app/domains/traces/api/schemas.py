from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import datetime

from app.domains.traces.constants import OPERATION_TYPES


class TraceResponse(BaseModel):
    id: int
    user_name: Optional[str] = None
    order_id: Optional[int] = None
    operation_name: Optional[str] = None
    operation_description: Optional[str] = None
    notes: Optional[str] = None
    test_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TracePaginatedResponse(BaseModel):
    items: List[TraceResponse]
    total: int
    skip: int
    limit: int

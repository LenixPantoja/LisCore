from pydantic import BaseModel, Field, computed_field
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


class ResultDeliveryRequest(BaseModel):
    """Datos de quien retira el resultado impreso."""
    receiver_name: str = Field(..., min_length=3, max_length=200)
    relationship: str = Field(..., min_length=2, max_length=100)
    document_number: str = Field(..., min_length=3, max_length=50)
    study_codes: Optional[List[str]] = Field(None, description="Estudios incluidos en la impresión (si fue parcial).")


class TracePaginatedResponse(BaseModel):
    items: List[TraceResponse]
    total: int
    skip: int
    limit: int

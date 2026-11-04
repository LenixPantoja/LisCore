from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkSheetBase(BaseModel):
    ws_name: str = Field(..., min_length=1, max_length=150)
    ws_description: Optional[str] = None
    ws_headquarter_id: Optional[int] = Field(None, description="NULL = todas las sedes")
    ws_work_group_id: Optional[int] = Field(None, description="Sector / área (Work_groups.wg_id)")
    ws_include_free_column: bool = False
    ws_active: bool = True


class WorkSheetCreate(WorkSheetBase):
    pass


class WorkSheetUpdate(BaseModel):
    ws_name: Optional[str] = Field(None, min_length=1, max_length=150)
    ws_description: Optional[str] = None
    ws_headquarter_id: Optional[int] = None
    ws_work_group_id: Optional[int] = None
    ws_include_free_column: Optional[bool] = None
    ws_active: Optional[bool] = None


class WorkSheetStudyItem(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    cups_code: Optional[str] = None
    work_group_id: Optional[int] = None
    work_group_name: Optional[str] = None
    order: int


class WorkSheetResponse(WorkSheetBase):
    ws_id: int
    headquarter_name: Optional[str] = None
    work_group_name: Optional[str] = None
    study_count: int = 0
    ws_created_at: Optional[datetime] = None
    ws_updated_at: Optional[datetime] = None


class WorkSheetDetailResponse(WorkSheetResponse):
    studies: List[WorkSheetStudyItem] = []


class WorkSheetPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[WorkSheetResponse]


class WorkSheetStudiesUpdate(BaseModel):
    """Estudios de la hoja en el orden de impresión (reemplaza los actuales)."""
    study_ids: List[int] = Field(default_factory=list, max_length=500)

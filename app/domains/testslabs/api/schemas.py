from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class TestsLabBase(BaseModel):
    code: str
    name: str
    name_abbreviation: Optional[str] = None
    technical_id: Optional[int] = None
    work_group_id: Optional[int] = None
    samples_type_id: Optional[int] = None
    units: Optional[str] = None
    format_for_complete: Optional[str] = None
    alarm_value_min: Optional[Decimal] = None
    alarm_value_max: Optional[Decimal] = None
    female_value_min: Optional[Decimal] = None
    female_value_max: Optional[Decimal] = None
    male_value_min: Optional[Decimal] = None
    male_value_max: Optional[Decimal] = None
    boys_value_min: Optional[Decimal] = None
    boys_value_max: Optional[Decimal] = None
    alternative_range_value: Optional[str] = None
    active: Optional[bool] = True
    test_type: Optional[str] = None
    is_confidential: Optional[bool] = False

class TestsLabCreate(TestsLabBase):
    pass

class TestsLabUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    name_abbreviation: Optional[str] = None
    technical_id: Optional[int] = None
    work_group_id: Optional[int] = None
    samples_type_id: Optional[int] = None
    units: Optional[str] = None
    format_for_complete: Optional[str] = None
    alarm_value_min: Optional[Decimal] = None
    alarm_value_max: Optional[Decimal] = None
    female_value_min: Optional[Decimal] = None
    female_value_max: Optional[Decimal] = None
    male_value_min: Optional[Decimal] = None
    male_value_max: Optional[Decimal] = None
    boys_value_min: Optional[Decimal] = None
    boys_value_max: Optional[Decimal] = None
    alternative_range_value: Optional[str] = None
    active: Optional[bool] = None
    test_type: Optional[str] = None
    is_confidential: Optional[bool] = None

class TestsLabResponse(TestsLabBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
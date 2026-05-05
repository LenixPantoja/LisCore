from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from app.domains.testslabs.domain.constants import RANGE_TYPES, AGE_TYPES


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
    num_decimal_result: Optional[int] = None
    is_confidential: Optional[bool] = False
    print_barcode: Optional[bool] = True


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
    num_decimal_result: Optional[int] = None
    is_confidential: Optional[bool] = None
    print_barcode: Optional[bool] = None


class TestsLabResponse(TestsLabBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- RangesReferences ---

class RangeReferenceBase(BaseModel):
    range_type: Optional[str] = None
    gender: Optional[str] = None
    age_type: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    priority: Optional[int] = None

    @field_validator("range_type")
    @classmethod
    def validate_range_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in RANGE_TYPES:
            raise ValueError(f"range_type inválido. Opciones: {RANGE_TYPES}")
        return v

    @field_validator("age_type")
    @classmethod
    def validate_age_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in AGE_TYPES:
            raise ValueError(f"age_type inválido. Opciones: {AGE_TYPES}")
        return v


class RangeReferenceCreate(RangeReferenceBase):
    range_type: str
    priority: int


class RangeReferenceUpdate(RangeReferenceBase):
    pass


class RangeReferenceResponse(RangeReferenceBase):
    id: int
    test_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RangeReferenceListResponse(BaseModel):
    total: int
    items: List[RangeReferenceResponse]


# --- ReferencesValues ---

class ReferenceValueBase(BaseModel):
    min_value: Optional[Decimal] = None
    max_values: Optional[Decimal] = None
    text_value: Optional[str] = None


class ReferenceValueCreate(ReferenceValueBase):
    pass


class ReferenceValueUpdate(ReferenceValueBase):
    pass


class ReferenceValueResponse(ReferenceValueBase):
    id: int
    ranges_references_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReferenceValueListResponse(BaseModel):
    total: int
    items: List[ReferenceValueResponse]

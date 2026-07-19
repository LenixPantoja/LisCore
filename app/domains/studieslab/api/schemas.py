from pydantic import BaseModel, model_validator
from typing import Optional, List, Any


# --- External Reference Laboratory ---
class ExternalReferenceLaboratoryResponse(BaseModel):
    erl_id: int
    erl_name: str

    class Config:
        from_attributes = True


# --- Studies Lab ---
class StudiesLabBase(BaseModel):
    code: str
    cups_code: Optional[str] = None
    name: str
    order_of_print: Optional[int] = None
    referral_location_id: Optional[int] = None
    work_groups_id: Optional[int] = None
    external_lab_id: Optional[int] = None
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
    external_lab_id: Optional[int] = None
    active: Optional[bool] = None


# --- Work Group ---
class WorkGroupResponse(BaseModel):
    wg_id: int
    wg_name: str

    class Config:
        from_attributes = True


# --- Tests Lab (Placeholder para la data completa de la prueba) ---
class TestsLabResponse(BaseModel):
    id: int
    code: str
    name: str
    active: bool
    units: Optional[str] = None
    st_sufix: Optional[int] = None

    @model_validator(mode='before')
    @classmethod
    def extract_st_sufix(cls, data: Any) -> Any:
        """
        Extrae st_sufix desde la relación sample_type del modelo TestsLab.
        """
        if isinstance(data, dict):
            return data
        # data es un objeto TestsLab (ORM)
        sample_type = getattr(data, 'sample_type', None)
        st_sufix = getattr(sample_type, 'st_sufix', None) if sample_type else None
        # Construir dict con los campos del schema + st_sufix
        result = {}
        for field_name in cls.model_fields:
            try:
                result[field_name] = getattr(data, field_name)
            except AttributeError:
                pass
        result['st_sufix'] = st_sufix
        return result

    class Config:
        from_attributes = True


class TestsLabPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[TestsLabResponse]


# --- Studies Test Detail ---
class StudiesTestDetailBase(BaseModel):
    tests_id: int
    order_print: Optional[int] = 0
    is_required: Optional[bool] = False
    work_group_id: Optional[int] = None


class StudiesTestDetailCreate(StudiesTestDetailBase):
    pass


class StudiesTestDetailUpdate(BaseModel):
    tests_id: Optional[int] = None
    order_print: Optional[int] = None
    is_required: Optional[bool] = None
    work_group_id: Optional[int] = None


class StudiesTestDetailResponse(StudiesTestDetailBase):
    id: int
    studies_id: int
    test: Optional[TestsLabResponse] = None
    work_group: Optional[WorkGroupResponse] = None

    class Config:
        from_attributes = True


# --- Combined Response ---
class StudiesLabResponse(StudiesLabBase):
    id: int
    work_group: Optional[WorkGroupResponse] = None
    external_lab: Optional[ExternalReferenceLaboratoryResponse] = None
    test_details: List[StudiesTestDetailResponse] = []

    class Config:
        from_attributes = True


class StudiesLabPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[StudiesLabResponse]
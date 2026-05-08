from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


# --- Analyzer Groups ---

class AnalyzerGroupBase(BaseModel):
    ag_name: Optional[str] = None
    ag_active: Optional[bool] = True

class AnalyzerGroupCreate(AnalyzerGroupBase):
    pass

class AnalyzerGroupUpdate(BaseModel):
    ag_name: Optional[str] = None
    ag_active: Optional[bool] = None

class AnalyzerGroupResponse(AnalyzerGroupBase):
    ag_id: int

    class Config:
        from_attributes = True

class AnalyzerGroupPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[AnalyzerGroupResponse]


# --- Analyzers ---

class AnalyzerBase(BaseModel):
    a_name: Optional[str] = None
    a_description: Optional[str] = None
    a_analyzer_group_id: Optional[int] = None
    a_work_group_id: Optional[int] = None
    a_licence: Optional[str] = None
    a_active: Optional[bool] = True

class AnalyzerCreate(AnalyzerBase):
    pass

class AnalyzerUpdate(BaseModel):
    a_name: Optional[str] = None
    a_description: Optional[str] = None
    a_analyzer_group_id: Optional[int] = None
    a_work_group_id: Optional[int] = None
    a_licence: Optional[str] = None
    a_active: Optional[bool] = None

class WorkGroupInfo(BaseModel):
    wg_id: int
    wg_code: Optional[str] = None
    wg_name: Optional[str] = None

    class Config:
        from_attributes = True

class AnalyzerResponse(AnalyzerBase):
    a_id: int
    a_created_at: Optional[datetime] = None
    a_updated_at: Optional[datetime] = None
    group: Optional[AnalyzerGroupResponse] = None
    work_group: Optional[WorkGroupInfo] = None

    class Config:
        from_attributes = True

class AnalyzerPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[AnalyzerResponse]


# --- Analyzer Details ---

class AnalyzerDetailBase(BaseModel):
    ad_analyzer_id: int
    ad_transmission_code: Optional[str] = None
    ad_receipt_code_results: Optional[str] = None
    ad_test_id: Optional[int] = None
    ad_sufix: Optional[str] = None
    ad_active: Optional[bool] = True

class AnalyzerDetailCreate(AnalyzerDetailBase):
    pass

class AnalyzerDetailUpdate(BaseModel):
    ad_transmission_code: Optional[str] = None
    ad_receipt_code_results: Optional[str] = None
    ad_test_id: Optional[int] = None
    ad_sufix: Optional[str] = None
    ad_active: Optional[bool] = None

class TestInfo(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None

    class Config:
        from_attributes = True

class AnalyzerDetailResponse(AnalyzerDetailBase):
    ad_id: int
    ad_created_at: Optional[date] = None
    ad_updated_at: Optional[date] = None
    test: Optional[TestInfo] = None

    class Config:
        from_attributes = True

class AnalyzerDetailPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[AnalyzerDetailResponse]

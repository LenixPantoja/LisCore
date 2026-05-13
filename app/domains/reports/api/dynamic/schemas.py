from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Allowed parameter types
# ---------------------------------------------------------------------------
ParameterType = Literal["date", "datetime", "text", "number", "select", "multiselect", "checkbox", "textarea"]


# ---------------------------------------------------------------------------
# ReportParameter schemas
# ---------------------------------------------------------------------------

class ReportParameterCreate(BaseModel):
    rp_name: str = Field(..., max_length=100)
    rp_label: str = Field(..., max_length=100)
    rp_type: ParameterType
    rp_required: bool = False
    rp_default_value: Optional[str] = None
    rp_source_query: Optional[str] = None
    rp_order_index: int = 0


class ReportParameterResponse(BaseModel):
    rp_id: int
    rp_name: str
    rp_label: str
    rp_type: str
    rp_required: bool
    rp_default_value: Optional[str] = None
    rp_order_index: int
    options: Optional[List[Dict[str, Any]]] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# DynamicReport schemas
# ---------------------------------------------------------------------------

class DynamicReportCreate(BaseModel):
    dr_name: str = Field(..., max_length=200)
    dr_description: Optional[str] = None
    dr_category_name: Optional[str] = Field(None, max_length=150)
    dr_sql_query: str = Field(..., description="Consulta SQL de solo lectura (SELECT)")
    dr_html_template: str = Field(..., description="Plantilla HTML con variables Jinja2")
    dr_active: bool = True
    parameters: List[ReportParameterCreate] = []


class DynamicReportUpdate(BaseModel):
    dr_name: Optional[str] = Field(None, max_length=200)
    dr_description: Optional[str] = None
    dr_category_name: Optional[str] = Field(None, max_length=150)
    dr_sql_query: Optional[str] = None
    dr_html_template: Optional[str] = None
    dr_active: Optional[bool] = None
    parameters: Optional[List[ReportParameterCreate]] = None


class DynamicReportSummary(BaseModel):
    dr_id: int
    dr_name: str
    dr_description: Optional[str] = None
    dr_category_name: Optional[str] = None
    dr_active: bool

    model_config = {"from_attributes": True}


class DynamicReportDetail(BaseModel):
    dr_id: int
    dr_name: str
    dr_description: Optional[str] = None
    dr_category_name: Optional[str] = None
    dr_active: bool
    parameters: List[ReportParameterResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Tree-style listing
# ---------------------------------------------------------------------------

class ReportTreeItem(BaseModel):
    """A single report entry inside a category node."""
    dr_id: int
    dr_name: str
    dr_description: Optional[str] = None
    dr_active: bool

    model_config = {"from_attributes": True}


class ReportCategoryNode(BaseModel):
    """A category with its nested list of reports."""
    category: Optional[str]
    reports: List[ReportTreeItem]


# ---------------------------------------------------------------------------
# Run / Export schemas
# ---------------------------------------------------------------------------

class RunReportRequest(BaseModel):
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Valores de los filtros definidos en ReportParameters. Claves = rp_name.",
    )


class RunReportResponse(BaseModel):
    report_id: int
    report_name: str
    total_rows: int
    html: str


class ExportReportPdfResponse(BaseModel):
    filename: str
    base64_pdf: str
    report_name: str
    total_rows: int

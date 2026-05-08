from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class LaboratoryReportRequest(BaseModel):
    order_id: int


class LaboratoryReportResponse(BaseModel):
    filename: str
    base64_pdf: str
    order_number: str
    patient_name: str


# --- Dashboard / Estadísticas ---

class OrderStateCount(BaseModel):
    state_id: int
    state_name: str
    total: int

class WorkGroupOrderCount(BaseModel):
    work_group: Optional[str] = None
    total_orders: int

class SedeOrderCount(BaseModel):
    hq_id: int
    sede: Optional[str] = None
    total_orders: int

class SedeStudyCount(BaseModel):
    hq_id: int
    sede: Optional[str] = None
    total_studies: int

class SedeLabCount(BaseModel):
    hq_id: int
    sede: Optional[str] = None
    total_labs: int

class PeriodCount(BaseModel):
    period: str
    total: int

class DashboardStatsResponse(BaseModel):
    total_orders_ingresadas: int
    total_orders_pendientes: int
    orders_by_state: List[OrderStateCount] = []
    orders_by_work_group: List[WorkGroupOrderCount] = []
    orders_by_sede: List[SedeOrderCount] = []
    studies_by_sede: List[SedeStudyCount] = []
    labs_by_sede: List[SedeLabCount] = []
    orders_by_day: List[PeriodCount] = []
    orders_by_month: List[PeriodCount] = []
    orders_by_year: List[PeriodCount] = []


# --- KPIs ---

class KpisResponse(BaseModel):
    total_orders: str
    total_pending_orders: str
    total_urgency_orders: str


class KpiWorkGroupItem(BaseModel):
    work_group: Optional[str] = None
    total_orders: int


class KpiOrdersByWorkGroupResponse(BaseModel):
    date: date
    orders_by_work_group: List[KpiWorkGroupItem]


class KpiSedeItem(BaseModel):
    hq_id: int
    sede: Optional[str] = None
    total_orders: int


class KpiOrdersBySedeResponse(BaseModel):
    date: date
    total_orders: int
    orders_by_sede: List[KpiSedeItem]


class KpiStateCount(BaseModel):
    state_id: int
    state_name: str
    total: int


class KpiPeriodItem(BaseModel):
    year: int
    month: int
    total_orders: int
    states: List[KpiStateCount]


class KpiOrdersByPeriodResponse(BaseModel):
    data: List[KpiPeriodItem]

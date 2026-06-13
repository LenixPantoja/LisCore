from pydantic import BaseModel
from typing import List, Optional
from datetime import date


MONTH_NAMES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


class ValidatedStudiesMonthItem(BaseModel):
    month: int
    month_name: str
    count: int


class ValidatedStudiesKpiResponse(BaseModel):
    year: int
    total: int
    data: List[ValidatedStudiesMonthItem]


class WeeklyTestsByAnalyzerItem(BaseModel):
    """Pruebas realizadas por un analizador en una semana específica"""
    week_start: str
    week_end: str
    analyzer_id: int
    analyzer_name: Optional[str] = "Sin asignar"
    total_tests: int


class WeeklyTestsByAnalyzerResponse(BaseModel):
    """Respuesta del KPI de pruebas semanales por analizador en un rango de fechas"""
    start_date: str
    end_date: str
    total: int
    data: List[WeeklyTestsByAnalyzerItem]
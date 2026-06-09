from pydantic import BaseModel
from typing import List


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

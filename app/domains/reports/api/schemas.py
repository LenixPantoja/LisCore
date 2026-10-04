from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class LaboratoryReportRequest(BaseModel):
    order_id: int
    study_ids: Optional[List[int]] = None


class SendWhatsAppResultsRequest(BaseModel):
    order_id: int
    phone_number: str


class SendWhatsAppResultsResponse(BaseModel):
    order_number: str
    patient_name: str
    phone_number: str
    message: str


class SendEmailResultsRequest(BaseModel):
    order_id: int
    email: str


class SendEmailResultsResponse(BaseModel):
    order_number: str
    patient_name: str
    email: str
    message: str


class LaboratoryReportResponse(BaseModel):
    filename: str
    base64_pdf: str
    order_number: str
    patient_name: str


# --- Datos estructurados de resultados (para plantillas externas) ---

class LaboratoryReportParametros(BaseModel):
    NOMBRE_PACIENTE: str
    DOCUMENTO_PACIENTE: str
    EMPRESA: str
    MUNICIPIO: str
    SERVICIO: str
    NUMERO_ORDEN: str
    EDAD: str
    GENERO: str
    FECHA_INGRESO_ORDEN: str
    LOGO1: Optional[str] = None
    LOGO2: Optional[str] = None
    MARCA_DE_AGUA: Optional[str] = None


class LaboratoryReportValidador(BaseModel):
    USUARIO_VALIDADOR: str
    FIRMA_BACTERIOLOGO: Optional[str] = None


class LaboratoryReportPrueba(BaseModel):
    NOMBRE_PRUEBA: str
    RESULTADO_PRUEBA: str
    VALOR_REFERENCIA: str
    RANGO_ALTERNATIVO: Optional[str] = None
    RESULTADO_COMPUESTO_PRUEBA: Optional[str] = None
    NOTAS_VALIDACION_PRUEBA: Optional[str] = None
    GRAFICA: Optional[str] = None


class LaboratoryReportEstudio(BaseModel):
    NOMBRE_ESTUDIO: str
    METODO: str
    FECHA_VALIDACION_ESTUDIO: Optional[str] = None
    VALIDADORES: List[LaboratoryReportValidador] = []
    pruebas: List[LaboratoryReportPrueba] = []


class LaboratoryReportGrupoTrabajo(BaseModel):
    GRUPO_TRABAJO: str
    estudios: List[LaboratoryReportEstudio] = []


class LaboratoryReportDataResponse(BaseModel):
    parametros: LaboratoryReportParametros
    grupos_trabajo: List[LaboratoryReportGrupoTrabajo] = []


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


# --- Dashboard: gráficas de producción ---

class ProductionByWorkGroupItem(BaseModel):
    work_group_id: Optional[int] = None
    work_group: Optional[str] = None
    total: int
    percentage: float


class ProductionByWorkGroupResponse(BaseModel):
    total: int
    items: List[ProductionByWorkGroupItem] = []


class TopStudyItem(BaseModel):
    study_id: int
    study_name: Optional[str] = None
    total: int


class TopStudiesResponse(BaseModel):
    items: List[TopStudyItem] = []


class StudiesByServiceItem(BaseModel):
    service_id: Optional[int] = None
    service_name: Optional[str] = None
    total: int
    percentage: float


class StudiesByServiceResponse(BaseModel):
    total: int
    items: List[StudiesByServiceItem] = []


class TopPatientItem(BaseModel):
    pt_id: int
    document: Optional[str] = None
    name: Optional[str] = None
    total_visits: int


class DashboardKpisSummaryResponse(BaseModel):
    total_patients: int
    male_patients: int
    female_patients: int
    total_orders: int
    total_tests: int
    avg_tests_per_order: float
    top_patient: Optional[TopPatientItem] = None

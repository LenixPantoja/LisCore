from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.reports.api.dynamic.schemas import (
    DynamicReportCreate,
    DynamicReportDetail,
    DynamicReportSummary,
    DynamicReportUpdate,
    ExportReportPdfRequest,
    ExportReportPdfResponse,
    ExportReportXlsxResponse,
    ReportCategoryNode,
    RunReportRequest,
    RunReportResponse,
)
from app.domains.reports.application.use_cases import dynamic_report_use_cases as use_cases

router = APIRouter(prefix="/dynamic", tags=["Dynamic Reports"])


@router.get(
    "",
    response_model=List[DynamicReportSummary],
    status_code=status.HTTP_200_OK,
    summary="Listar reportes dinámicos",
    description="Retorna todos los reportes dinámicos activos.",
    dependencies=[Depends(require_permission("Reports:DynamicList"))],
)
async def list_dynamic_reports(db: AsyncSession = Depends(get_db)):
    return await use_cases.list_reports(db)


@router.post(
    "",
    response_model=DynamicReportSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Crear reporte dinámico",
    description="Crea un nuevo reporte dinámico con su SQL, plantilla HTML y parámetros de filtro.",
    dependencies=[Depends(require_permission("Reports:DynamicCreate"))],
)
async def create_dynamic_report(
    body: DynamicReportCreate,
    db: AsyncSession = Depends(get_db),
):
    report_data = body.model_dump(exclude={"parameters"})
    params_data = [p.model_dump() for p in body.parameters]
    return await use_cases.create_report(db, report_data, params_data)


@router.get(
    "/tree",
    response_model=List[ReportCategoryNode],
    status_code=status.HTTP_200_OK,
    summary="Árbol de reportes por categoría",
    description=(
        "Retorna los reportes dinámicos activos agrupados por categoría. "
        "Cada nodo contiene la categoría y la lista de reportes que pertenecen a ella. "
        "Los reportes sin categoría aparecen con category=null."
    ),
    dependencies=[Depends(require_permission("Reports:DynamicList"))],
)
async def list_dynamic_reports_tree(db: AsyncSession = Depends(get_db)):
    return await use_cases.list_reports_tree(db)


@router.get(
    "/{report_id}",
    response_model=DynamicReportDetail,
    status_code=status.HTTP_200_OK,
    summary="Detalle de reporte dinámico",
    description=(
        "Retorna el reporte con sus parámetros. "
        "Para parámetros de tipo select/multiselect, ejecuta la source_query y devuelve las opciones disponibles."
    ),
    dependencies=[Depends(require_permission("Reports:DynamicRead"))],
)
async def get_dynamic_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.get_report_detail(db, report_id)


@router.put(
    "/{report_id}",
    response_model=DynamicReportSummary,
    status_code=status.HTTP_200_OK,
    summary="Actualizar reporte dinámico",
    description=(
        "Actualiza los campos del reporte. "
        "Si se envía 'parameters', reemplaza todos los parámetros existentes por los nuevos."
    ),
    dependencies=[Depends(require_permission("Reports:DynamicUpdate"))],
)
async def update_dynamic_report(
    report_id: int,
    body: DynamicReportUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = body.model_dump(exclude_none=True, exclude={"parameters"})
    params_data = [p.model_dump() for p in body.parameters] if body.parameters is not None else None
    return await use_cases.update_report(db, report_id, update_data, params_data)


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desactivar reporte dinámico",
    description="Realiza una baja lógica del reporte (dr_active = false).",
    dependencies=[Depends(require_permission("Reports:DynamicDelete"))],
)
async def delete_dynamic_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    await use_cases.delete_report(db, report_id)


@router.post(
    "/{report_id}/run",
    response_model=RunReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar reporte dinámico",
    description=(
        "Ejecuta el SQL del reporte con los parámetros enviados, "
        "renderiza la plantilla HTML con Jinja2 y devuelve el HTML listo para mostrar."
    ),
    dependencies=[Depends(require_permission("Reports:DynamicRun"))],
)
async def run_dynamic_report(
    report_id: int,
    body: RunReportRequest,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.run_report(db, report_id, body.params)


@router.post(
    "/{report_id}/export-pdf",
    response_model=ExportReportPdfResponse,
    status_code=status.HTTP_200_OK,
    summary="Exportar reporte a PDF",
    description=(
        "Ejecuta el reporte con los parámetros dados, genera un PDF y lo devuelve codificado en base64. "
        "Admite control de tamaño de hoja ('carta'/'oficio') y orientación ('portrait'/'landscape')."
    ),
    dependencies=[Depends(require_permission("Reports:DynamicExportPdf"))],
)
async def export_dynamic_report_pdf(
    report_id: int,
    body: ExportReportPdfRequest,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.export_report_pdf(
        db, report_id, body.params, body.page_size, body.orientation
    )


@router.post(
    "/{report_id}/export-xlsx",
    response_model=ExportReportXlsxResponse,
    status_code=status.HTTP_200_OK,
    summary="Exportar reporte a Excel (XLSX)",
    description=(
        "Ejecuta el reporte con los parámetros dados, genera un archivo XLSX y lo devuelve codificado en base64."
    ),
    dependencies=[Depends(require_permission("Reports:DynamicExportPdf"))],
)
async def export_dynamic_report_xlsx(
    report_id: int,
    body: RunReportRequest,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.export_report_xlsx(db, report_id, body.params)

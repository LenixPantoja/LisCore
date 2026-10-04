"""
Router v2 del dominio de reportes.

Por ahora expone únicamente la v2 de /laboratory-results, que delega el
renderizado del PDF a un servicio externo en vez de generarlo localmente
con reportlab (ver app/integrations/pdf_renderer/client.py).
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.reports.api.schemas import LaboratoryReportRequest, LaboratoryReportResponse
from app.domains.reports.application.use_cases import report_use_cases as use_cases

router = APIRouter()


@router.post(
    "/laboratory-results",
    response_model=LaboratoryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar PDF de resultados de laboratorio (v2 — renderizado externo)",
    description=(
        "Funciona igual que /api/reports/laboratory-results (solo estudios "
        "completamente validados, mismos PDFs anexos fusionados al final), pero "
        "en vez de generar el PDF localmente arma los mismos datos estructurados "
        "que /api/reports/laboratory-results/report-data y se los envía al "
        "servicio externo de renderizado de PDF (POST "
        "http://<host-de-este-backend>:PDF_RENDERER_PORT/api/reports/resultado-laboratorio), "
        "que responde con el PDF ya armado en crudo. El host del servicio externo "
        "se toma del mismo host con el que se llamó a esta API — debe correr en "
        "la misma máquina/host que este backend."
    ),
    dependencies=[Depends(require_permission("Reports:GenerateReport"))],
)
async def generate_laboratory_report_v2(
    request: LaboratoryReportRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    renderer_host = http_request.url.hostname or "localhost"
    return await use_cases.generate_laboratory_report_v2(
        db, request.order_id, renderer_host, request.study_ids
    )

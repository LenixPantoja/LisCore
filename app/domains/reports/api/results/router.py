from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.reports.api.schemas import (
    LaboratoryReportRequest,
    LaboratoryReportResponse,
)
from app.domains.reports.application.use_cases.results import results_use_cases

router = APIRouter()


@router.post(
    "/laboratory-results/raw",
    response_model=LaboratoryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar PDF de resultados de laboratorio (sin filtros de estado)",
    description=(
        "Recibe el ID de una orden y retorna el reporte de resultados en formato PDF "
        "codificado en Base64. A diferencia de /laboratory-results, este endpoint NO "
        "filtra por estado de los laboratorios ni de la orden: muestra todos los "
        "resultados registrados tal cual están."
    ),
    dependencies=[Depends(require_permission("Reports:GenerateReport"))],
)
async def generate_laboratory_report_raw(
    request: LaboratoryReportRequest,
    db: AsyncSession = Depends(get_db),
):
    return await results_use_cases.generate_laboratory_report_raw(db, request.order_id)
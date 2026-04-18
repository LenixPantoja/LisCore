from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.reports.api.schemas import LaboratoryReportRequest, LaboratoryReportResponse
from app.domains.reports.application.use_cases import report_use_cases as use_cases

router = APIRouter()


@router.post(
    "/laboratory-results",
    response_model=LaboratoryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar PDF de resultados de laboratorio",
    description="Recibe el ID de una orden y retorna el reporte de resultados en formato PDF codificado en Base64.",
)
async def generate_laboratory_report(
    request: LaboratoryReportRequest,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.generate_laboratory_report(db, request.order_id)

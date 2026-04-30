from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.domains.reports.api.schemas import (
    LaboratoryReportRequest, LaboratoryReportResponse,
    DashboardStatsResponse,
    KpisResponse,
)
from app.domains.reports.application.use_cases import report_use_cases as use_cases
from app.domains.reports.application.use_cases import stats_use_cases
from app.domains.reports.application.use_cases import kpis_use_cases
from app.domains.reports.api.pos.router import router as pos_router
from app.domains.reports.api.printer_barcodes.router import router as barcodes_router

router = APIRouter()

# Include sub-routers
router.include_router(pos_router)
router.include_router(barcodes_router)


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


@router.get(
    "/dashboard/stats",
    response_model=DashboardStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Estadísticas del dashboard",
    description="Retorna métricas de órdenes, estudios y pruebas agrupadas por estado, work group, sede y período de tiempo.",
)
async def get_dashboard_stats(
    date_from: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    headquarter_id: Optional[int] = Query(None, description="Filtrar por sede"),
    db: AsyncSession = Depends(get_db),
):
    return await stats_use_cases.get_dashboard_stats(db, date_from, date_to, headquarter_id)


@router.get(
    "/kpis",
    response_model=KpisResponse,
    status_code=status.HTTP_200_OK,
    summary="KPIs de órdenes",
    description="Retorna el total de órdenes registradas y el total de órdenes con estado Pendiente (o_state=2).",
)
async def get_kpis(
    db: AsyncSession = Depends(get_db),
):
    return await kpis_use_cases.get_kpis(db)

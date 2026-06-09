from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.reports.api.schemas import (
    LaboratoryReportRequest, LaboratoryReportResponse,
    DashboardStatsResponse,
    KpisResponse,
    KpiOrdersByWorkGroupResponse,
    KpiOrdersBySedeResponse,
    KpiOrdersByPeriodResponse,
    SendWhatsAppResultsRequest, SendWhatsAppResultsResponse,
    SendEmailResultsRequest, SendEmailResultsResponse,
)
from app.domains.reports.application.use_cases import report_use_cases as use_cases
from app.domains.reports.application.use_cases import stats_use_cases
from app.domains.reports.application.use_cases import kpis_use_cases
from app.domains.reports.application.use_cases import send_whatsapp_results
from app.domains.reports.application.use_cases import send_email_results
from app.domains.reports.api.pos.router import router as pos_router
from app.domains.reports.api.printer_barcodes.router import router as barcodes_router
from app.domains.reports.api.dynamic.router import router as dynamic_reports_router
from app.domains.reports.api.results.router import router as results_router

router = APIRouter()

# Include sub-routers
router.include_router(pos_router)
router.include_router(barcodes_router)
router.include_router(dynamic_reports_router)
router.include_router(results_router)


@router.post(
    "/laboratory-results",
    response_model=LaboratoryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar PDF de resultados de laboratorio",
    description="Recibe el ID de una orden y retorna el reporte de resultados en formato PDF codificado en Base64.",
    dependencies=[Depends(require_permission("Reports:GenerateReport"))],
)
async def generate_laboratory_report(
    request: LaboratoryReportRequest,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.generate_laboratory_report(db, request.order_id)


@router.post(
    "/whatsapp/send-results",
    response_model=SendWhatsAppResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Enviar resultados por WhatsApp",
    description="Genera el PDF de resultados de la orden y lo envía al número de teléfono indicado via WhatsApp.",
    dependencies=[Depends(require_permission("Reports:SendWhatsApp"))],
)
async def send_results_via_whatsapp(
    request: SendWhatsAppResultsRequest,
    db: AsyncSession = Depends(get_db),
):
    return await send_whatsapp_results.execute(db, request.order_id, request.phone_number)


@router.post(
    "/email/send-results",
    response_model=SendEmailResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Enviar resultados por correo electrónico",
    description="Genera el PDF de resultados de la orden y lo envía al correo electrónico indicado via Gmail.",
    dependencies=[Depends(require_permission("Reports:SendEmail"))],
)
async def send_results_via_email(
    request: SendEmailResultsRequest,
    db: AsyncSession = Depends(get_db),
):
    return await send_email_results.execute(db, request.order_id, request.email)


@router.get(
    "/dashboard/stats",
    response_model=DashboardStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Estadísticas del dashboard",
    description="Retorna métricas de órdenes, estudios y pruebas agrupadas por estado, work group, sede y período de tiempo.",
    dependencies=[Depends(require_permission("Reports:Dashboard"))],
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
    dependencies=[Depends(require_permission("Reports:Kpis"))],
)
async def get_kpis(
    db: AsyncSession = Depends(get_db),
):
    return await kpis_use_cases.get_kpis(db)


@router.get(
    "/kpis/orders-by-work-group",
    response_model=KpiOrdersByWorkGroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Órdenes por grupo de trabajo en una fecha",
    description="Dado una fecha (YYYY-MM-DD), retorna la cantidad de órdenes agrupadas por grupo de trabajo.",
    dependencies=[Depends(require_permission("Reports:Kpis"))],
)
async def get_kpi_orders_by_work_group(
    date: date = Query(..., description="Fecha de consulta (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    return await kpis_use_cases.get_orders_by_work_group_by_date(db, date)


@router.get(
    "/kpis/orders-by-sede",
    response_model=KpiOrdersBySedeResponse,
    status_code=status.HTTP_200_OK,
    summary="Órdenes por sede en una fecha",
    description="Dado una fecha (YYYY-MM-DD), retorna la cantidad de órdenes por sede y el total general.",
    dependencies=[Depends(require_permission("Reports:Kpis"))],
)
async def get_kpi_orders_by_sede(
    date: date = Query(..., description="Fecha de consulta (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    return await kpis_use_cases.get_orders_by_sede_by_date(db, date)


@router.get(
    "/kpis/orders-by-period",
    response_model=KpiOrdersByPeriodResponse,
    status_code=status.HTTP_200_OK,
    summary="Órdenes por mes/año con estados",
    description="Retorna la cantidad de órdenes agrupadas por mes y año, con el desglose por estado de la orden. Acepta filtros opcionales de rango de fechas.",
    dependencies=[Depends(require_permission("Reports:Kpis"))],
)
async def get_kpi_orders_by_period(
    date_from: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    return await kpis_use_cases.get_orders_by_period(db, date_from, date_to)

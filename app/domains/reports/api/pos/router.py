from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.reports.api.pos.schemas import POSTicketRequest, POSTicketResponse
from app.domains.reports.application.use_cases.pos import pos_use_cases

router = APIRouter()


@router.post(
    "/pos-ticket",
    response_model=POSTicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar ticket POS 80mm",
    description=(
        "Dado el ID de una orden, genera un ticket POS de 80mm en PDF codificado en Base64. "
        "El ticket incluye: (1) cabecera con datos de la empresa LISCORE, "
        "(2) datos del paciente y la orden, "
        "(3) tabla de exámenes con valores de tarifa, "
        "(4) total y pie de página con disclaimer fiscal."
    ),
    tags=["Reports - POS"],
)
async def generate_pos_ticket(
    request: POSTicketRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an 80mm POS ticket for an order.

    - **order_id**: ID of the order to print.

    **Returns** a PDF encoded in Base64 with:
    - Header 1: LISCORE company data (name, NIT, address, phone, email).
    - Header 2: Patient info (name, document, type, age, sex, phone, insurance,
      CIE10 diagnosis, priority, email, address, order number, entry date,
      print date, attended by).
    - Body: table with item, exam name and tariff value per study.
    - Footer: fiscal disclaimer text.

    **Errors:**
    - 404: Order not found.
    """
    return await pos_use_cases.generate_pos_ticket(db, request.order_id)

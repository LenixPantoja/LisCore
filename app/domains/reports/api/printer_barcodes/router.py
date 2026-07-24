from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.reports.api.printer_barcodes.schemas import (
    BarcodeStickerRequest,
    BarcodeStickerResponse,
)
from app.domains.reports.application.use_cases.printer_barcodes import barcode_use_cases

router = APIRouter()


@router.post(
    "/printer-barcodes",
    response_model=BarcodeStickerResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar stickers de código de barras para tubos",
    description=(
        "Dado el ID de una orden, genera un PDF con los stickers para marcar los tubos. "
        "Cada sticker incluye: nombre del paciente, número de documento, empresa, edad, "
        "grupo de trabajo, número de orden con sufijo, código de barras del tubo y "
        "las pruebas asociadas al área y tipo de muestra. Si se envía `study_ids` "
        "(opcional), solo se generan los stickers de los tubos donde se encuentran esos "
        "estudios, en vez de todos los tubos de la orden."
    ),
    tags=["Reports - Barcodes"],
)
async def generate_barcode_stickers(
    request: BarcodeStickerRequest,
    db: AsyncSession = Depends(get_db),
):
    return await barcode_use_cases.generate_barcode_stickers(db, request.order_id, request.study_ids)

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.barcodes.domain.models import Barcode

LABEL_TYPE_MUESTRA = "MUESTRA"
LABEL_TYPE_GRADILLA = "GRADILLA"
# Etiqueta de la orden (sede, número, convenio, paciente). Se imprime al final
# de los stickers de muestras, solo si hay una plantilla activa.
LABEL_TYPE_ORDEN = "ORDEN"


@dataclass(frozen=True)
class LabelTemplate:
    zpl: str
    copies: int  # barcodes.number_labels_print


class BarcodeRepository:
    @staticmethod
    async def find_active(db: AsyncSession, label_type: str) -> Optional[LabelTemplate]:
        """Plantilla activa (is_active=1) del tipo indicado, o None si no hay."""
        result = await db.execute(
            select(Barcode.barcode, Barcode.number_labels_print)
            .where(Barcode.label_type == label_type, Barcode.is_active == 1)
            .order_by(Barcode.id)
            .limit(1)
        )
        row = result.first()
        if not row or not row.barcode:
            return None
        return LabelTemplate(zpl=row.barcode, copies=max(int(row.number_labels_print or 1), 1))

    @staticmethod
    async def get_active(db: AsyncSession, label_type: str) -> LabelTemplate:
        """Como find_active, pero falla con 500 si no hay plantilla activa."""
        template = await BarcodeRepository.find_active(db, label_type)
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No hay una plantilla ZPL activa configurada para '{label_type}' en la tabla barcodes.",
            )
        return template

    @staticmethod
    async def get_active_template(db: AsyncSession, label_type: str) -> str:
        """Retorna el ZPL activo (is_active=1) para el tipo de etiqueta indicado."""
        return (await BarcodeRepository.get_active(db, label_type)).zpl

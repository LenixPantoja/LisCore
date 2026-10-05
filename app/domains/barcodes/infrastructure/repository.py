from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.barcodes.domain.models import Barcode

LABEL_TYPE_MUESTRA = "MUESTRA"
LABEL_TYPE_GRADILLA = "GRADILLA"


class BarcodeRepository:
    @staticmethod
    async def get_active_template(db: AsyncSession, label_type: str) -> str:
        """Retorna el ZPL activo (is_active=1) para el tipo de etiqueta indicado."""
        result = await db.execute(
            select(Barcode.barcode)
            .where(Barcode.label_type == label_type, Barcode.is_active == 1)
            .limit(1)
        )
        template = result.scalars().first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No hay una plantilla ZPL activa configurada para '{label_type}' en la tabla barcodes.",
            )
        return template

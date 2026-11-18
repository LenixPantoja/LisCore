"""
Homologación del servicio que envía el HIS (código + nombre) contra el
catálogo "Services".

Orden de búsqueda:
  1. Por código exacto (sin espacios), prefiriendo servicios activos.
  2. Por nombre (sin distinguir mayúsculas ni espacios extremos).
  3. Si no existe (o el HIS no envía servicio), se asigna el servicio por
     defecto con código "0" (CE - LABORATORIO). Nunca crea servicios.
"""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.masters.domain.models import Service

# Servicio asignado cuando el del HIS no existe en el catálogo
DEFAULT_SERVICE_CODE = "0"  # CE - LABORATORIO


def _clean(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


async def resolve_service_id(
    db: AsyncSession,
    code: Optional[str],
    name: Optional[str],
    use_default: bool = True,
) -> Optional[int]:
    code = _clean(code)
    name = _clean(name)

    if code:
        res = await db.execute(
            select(Service.id)
            .where(func.trim(Service.code) == code)
            .order_by(Service.active.desc().nulls_last(), Service.id)
            .limit(1)
        )
        sid = res.scalar_one_or_none()
        if sid:
            return sid

    if name:
        res = await db.execute(
            select(Service.id)
            .where(func.upper(func.trim(Service.name)) == name.upper())
            .order_by(Service.active.desc().nulls_last(), Service.id)
            .limit(1)
        )
        sid = res.scalar_one_or_none()
        if sid:
            return sid

    if not use_default:
        return None

    # No existe en el catálogo: se asigna el servicio por defecto (código "0")
    res = await db.execute(
        select(Service.id)
        .where(func.trim(Service.code) == DEFAULT_SERVICE_CODE)
        .order_by(Service.active.desc().nulls_last(), Service.id)
        .limit(1)
    )
    return res.scalar_one_or_none()

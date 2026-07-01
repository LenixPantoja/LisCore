from typing import Optional
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.seroteca.infrastructure.repository import SerotecaRepository, GradillaRepository, TipoGradillaRepository
from utils.timezone import get_bogota_now


# ── Serotecas ────────────────────────────────────────────────────────────────

async def create_seroteca(db: AsyncSession, data: dict) -> dict:
    return await SerotecaRepository.create(db, data)


async def get_seroteca(db: AsyncSession, s_id: int) -> dict:
    item = await SerotecaRepository.get_by_id(db, s_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")
    return item


async def list_serotecas(
    db: AsyncSession,
    skip: int,
    limit: int,
    search: Optional[str],
    active_only: bool,
    headquarter_id: Optional[int] = None,
) -> dict:
    items, total = await SerotecaRepository.list_paginated(
        db, skip, limit, search, active_only, headquarter_id
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


async def update_seroteca(db: AsyncSession, s_id: int, data: dict) -> dict:
    item = await SerotecaRepository.update(db, s_id, data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")
    return item


async def delete_seroteca(db: AsyncSession, s_id: int) -> dict:
    deleted = await SerotecaRepository.delete(db, s_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")
    return {"detail": "Seroteca deleted"}


# ── Gradillas ────────────────────────────────────────────────────────────────

async def create_rack(db: AsyncSession, data: dict) -> dict:
    # If g_tipo_gradilla_id is provided, auto-fill rows + cols from the template
    tipo = None
    if data.get("g_tipo_gradilla_id"):
        tipo = await TipoGradillaRepository.get_by_id(db, data["g_tipo_gradilla_id"])
        if not tipo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de gradilla not found")
        # Fill dimensions from template if not explicitly provided (None or missing)
        if not data.get("g_rows"):
            data["g_rows"] = tipo.tg_rows
        if not data.get("g_cols"):
            data["g_cols"] = tipo.tg_cols
        # Calculate discard date based on tipo storage days
        if tipo.tg_storage_days and not data.get("g_discard_date"):
            data["g_discard_date"] = get_bogota_now() + timedelta(days=tipo.tg_storage_days)

    # Auto-generate consecutive number: DDMMAA-CONSECUTIVO
    from utils.Consecutives.consecutive_gradillas import generate_gradilla_number
    data["g_number"] = await generate_gradilla_number(db)

    return await GradillaRepository.create(db, data)


async def get_rack(db: AsyncSession, g_id: int) -> dict:
    rack = await GradillaRepository.get_by_id(db, g_id)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    return rack


async def list_racks(
    db: AsyncSession, s_id: int, skip: int, limit: int, search: Optional[str] = None
) -> dict:
    items, total = await GradillaRepository.list_by_seroteca(db, s_id, skip, limit, search)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


async def update_rack(db: AsyncSession, g_id: int, data: dict) -> dict:
    rack = await GradillaRepository.update(db, g_id, data)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    return rack


async def delete_rack(db: AsyncSession, g_id: int) -> dict:
    deleted = await GradillaRepository.delete(db, g_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    return {"detail": "Rack and all its positions deleted"}


# ── Tipos de Gradilla ─────────────────────────────────────────────────────────

async def create_tipo_gradilla(db: AsyncSession, data: dict) -> dict:
    return await TipoGradillaRepository.create(db, data)


async def get_tipo_gradilla(db: AsyncSession, tg_id: int) -> dict:
    item = await TipoGradillaRepository.get_by_id(db, tg_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de gradilla not found")
    return item


async def list_tipos_gradilla(
    db: AsyncSession,
    skip: int,
    limit: int,
    search: Optional[str] = None,
    active_only: bool = False,
) -> dict:
    items, total = await TipoGradillaRepository.list_paginated(db, skip, limit, search, active_only)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


async def update_tipo_gradilla(db: AsyncSession, tg_id: int, data: dict) -> dict:
    item = await TipoGradillaRepository.update(db, tg_id, data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de gradilla not found")
    return item


async def delete_tipo_gradilla(db: AsyncSession, tg_id: int) -> dict:
    deleted = await TipoGradillaRepository.delete(db, tg_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de gradilla not found")
    return {"detail": "Tipo de gradilla deleted"}


# ── Gradilla Sticker Generation ──────────────────────────────────────────────

async def generate_gradilla_sticker(db: AsyncSession, g_id: int) -> dict:
    """Generate a ZPL + PDF sticker for a gradilla rack."""
    from app.domains.seroteca.infrastructure.gradilla_sticker import generate_sticker

    rack = await GradillaRepository.get_by_id(db, g_id)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gradilla not found")

    return generate_sticker(rack)
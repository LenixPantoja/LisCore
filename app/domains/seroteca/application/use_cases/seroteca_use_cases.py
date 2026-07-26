from typing import Optional
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.seroteca.infrastructure.repository import SerotecaRepository, GradillaRepository, TipoGradillaRepository
from app.domains.traces.constants import OPERATION_MANAGE_SEROTECA, OPERATION_MANAGE_GRADILLA
from app.domains.traces.models import AppTrace
from app.domains.seroteca.domain.models import Seroteca, Gradilla
from utils.timezone import get_bogota_now


def _add_trace(db: AsyncSession, user_id: int | None, op_type: int, description: str, notes: str | None = None):
    if user_id:
        db.add(AppTrace(
            usr_id=user_id,
            operation_type=op_type,
            operation_description=description,
            notes=notes,
        ))


# ── Serotecas ────────────────────────────────────────────────────────────────

async def create_seroteca(db: AsyncSession, data: dict, user_id: int | None = None) -> dict:
    result = await SerotecaRepository.create(db, data)
    _add_trace(
        db, user_id, OPERATION_MANAGE_SEROTECA,
        f"Creación de seroteca {result.s_name}",
        f"ID: {result.s_id} | Nombre: {result.s_name} | Sede: {result.s_headquarter_id}",
    )
    await db.commit()
    return result


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


async def update_seroteca(db: AsyncSession, s_id: int, data: dict, user_id: int | None = None) -> dict:
    # Snapshot before
    before = await SerotecaRepository.get_by_id(db, s_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")

    editable_fields = ["s_name", "s_description", "s_location_id", "s_headquarter_id", "s_active"]
    field_labels = {
        "s_name": "Nombre", "s_description": "Descripción",
        "s_location_id": "Ubicación", "s_headquarter_id": "Sede", "s_active": "Activo",
    }

    before_snap = {f: getattr(before, f, None) for f in editable_fields}

    item = await SerotecaRepository.update(db, s_id, data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")

    diff = []
    for f in editable_fields:
        if f in data and data[f] is not None:
            old = before_snap.get(f)
            new = data[f]
            if old != new:
                diff.append(f"{field_labels.get(f, f)}: {old} → {new}")

    if diff:
        _add_trace(
            db, user_id, OPERATION_MANAGE_SEROTECA,
            f"Edición de seroteca {item.s_name}",
            " | ".join(diff),
        )
        await db.commit()

    return item


async def delete_seroteca(db: AsyncSession, s_id: int, user_id: int | None = None) -> dict:
    before = await SerotecaRepository.get_by_id(db, s_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")
    name = before.s_name
    deleted = await SerotecaRepository.delete(db, s_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")
    _add_trace(
        db, user_id, OPERATION_MANAGE_SEROTECA,
        f"Eliminación de seroteca {name}",
        f"ID: {s_id} | Nombre: {name}",
    )
    await db.commit()
    return {"detail": "Seroteca deleted"}


# ── Gradillas ────────────────────────────────────────────────────────────────

async def create_rack(db: AsyncSession, data: dict, user_id: int | None = None) -> dict:
    # If g_tipo_gradilla_id is provided, auto-fill rows + cols from the template
    tipo = None
    if data.get("g_tipo_gradilla_id"):
        tipo = await TipoGradillaRepository.get_by_id(db, data["g_tipo_gradilla_id"])
        if not tipo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de gradilla not found")
        if not data.get("g_rows"):
            data["g_rows"] = tipo.tg_rows
        if not data.get("g_cols"):
            data["g_cols"] = tipo.tg_cols
        if tipo.tg_storage_days and not data.get("g_discard_date"):
            data["g_discard_date"] = get_bogota_now() + timedelta(days=tipo.tg_storage_days)

    from utils.Consecutives.consecutive_gradillas import generate_gradilla_number
    data["g_number"] = await generate_gradilla_number(db)

    result = await GradillaRepository.create(db, data)
    _add_trace(
        db, user_id, OPERATION_MANAGE_GRADILLA,
        f"Creación de gradilla {result.g_name}",
        f"ID: {result.g_id} | Número: {result.g_number} | Seroteca: {result.g_seroteca_id} | {result.g_rows}x{result.g_cols}",
    )
    await db.commit()
    return result


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


async def update_rack(db: AsyncSession, g_id: int, data: dict, user_id: int | None = None) -> dict:
    before = await GradillaRepository.get_by_id(db, g_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")

    editable_fields = ["g_name", "g_rows", "g_cols", "g_discard_date", "g_active"]
    field_labels = {
        "g_name": "Nombre", "g_rows": "Filas", "g_cols": "Columnas",
        "g_discard_date": "Fecha descarte", "g_active": "Activo",
    }
    before_snap = {f: getattr(before, f, None) for f in editable_fields}

    rack = await GradillaRepository.update(db, g_id, data)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")

    diff = []
    for f in editable_fields:
        if f in data and data[f] is not None:
            old = before_snap.get(f)
            new = data[f]
            if old != new:
                diff.append(f"{field_labels.get(f, f)}: {old} → {new}")

    if diff:
        _add_trace(
            db, user_id, OPERATION_MANAGE_GRADILLA,
            f"Edición de gradilla {rack.g_name}",
            " | ".join(diff),
        )
        await db.commit()

    return rack


async def delete_rack(db: AsyncSession, g_id: int, user_id: int | None = None) -> dict:
    before = await GradillaRepository.get_by_id(db, g_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    name = before.g_name
    number = before.g_number
    deleted = await GradillaRepository.delete(db, g_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    _add_trace(
        db, user_id, OPERATION_MANAGE_GRADILLA,
        f"Eliminación de gradilla {name}",
        f"ID: {g_id} | Número: {number} | Nombre: {name}",
    )
    await db.commit()
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
    from app.domains.seroteca.infrastructure.gradilla_sticker import generate_sticker

    rack = await GradillaRepository.get_by_id(db, g_id)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gradilla not found")

    return generate_sticker(rack)
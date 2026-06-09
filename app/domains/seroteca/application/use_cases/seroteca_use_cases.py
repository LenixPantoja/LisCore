from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.seroteca.infrastructure.repository import SerotecaRepository, GradillaRepository


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
    return await GradillaRepository.create(db, data)


async def get_rack(db: AsyncSession, g_id: int) -> dict:
    rack = await GradillaRepository.get_by_id(db, g_id)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    return rack


async def list_racks(db: AsyncSession, s_id: int, skip: int, limit: int) -> dict:
    items, total = await GradillaRepository.list_by_seroteca(db, s_id, skip, limit)
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

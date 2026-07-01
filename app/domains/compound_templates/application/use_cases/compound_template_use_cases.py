from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.domains.compound_templates.infrastructure.repository import CompoundTemplateRepository


async def create_template(db: AsyncSession, data: dict):
    try:
        # Convertir CompoundTemplatePayload → dict para JSONB
        if "ct_template" in data and not isinstance(data["ct_template"], dict):
            ct_val = data["ct_template"]
            if hasattr(ct_val, "model_dump"):
                data["ct_template"] = ct_val.model_dump()
            elif hasattr(ct_val, "dict"):
                data["ct_template"] = ct_val.dict()

        template = await CompoundTemplateRepository.create(db, data)
        await db.commit()
        await db.refresh(template)
        return template
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad al crear la plantilla.",
        )


async def list_templates(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active_only: bool = False,
):
    items, total = await CompoundTemplateRepository.get_paginated(
        db, skip, limit, search, active_only
    )
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
    }


async def get_template(db: AsyncSession, ct_id: int):
    template = await CompoundTemplateRepository.get_by_id(db, ct_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )
    return template


async def update_template(db: AsyncSession, ct_id: int, data: dict):
    try:
        # Convertir CompoundTemplatePayload → dict para JSONB
        if "ct_template" in data and not isinstance(data["ct_template"], dict):
            ct_val = data["ct_template"]
            if hasattr(ct_val, "model_dump"):
                data["ct_template"] = ct_val.model_dump()
            elif hasattr(ct_val, "dict"):
                data["ct_template"] = ct_val.dict()

        template = await CompoundTemplateRepository.update(db, ct_id, data)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantilla no encontrada.",
            )
        await db.commit()
        await db.refresh(template)
        return template
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad al actualizar la plantilla.",
        )


async def delete_template(db: AsyncSession, ct_id: int):
    success = await CompoundTemplateRepository.delete(db, ct_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )
    await db.commit()
    return {"success": True, "message": "Plantilla eliminada correctamente."}


# ── N:M links ──────────────────────────────────────────────────────────────────

async def add_test_to_template(db: AsyncSession, ct_id: int, data: dict):
    template = await CompoundTemplateRepository.get_by_id(db, ct_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )
    try:
        link = await CompoundTemplateRepository.add_test_link(db, ct_id, data)
        await db.commit()
        await db.refresh(link)
        return link
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad al vincular test con plantilla. Verifique que el test exista.",
        )


async def get_template_test_links(db: AsyncSession, ct_id: int):
    template = await CompoundTemplateRepository.get_by_id(db, ct_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )
    return await CompoundTemplateRepository.get_test_links(db, ct_id)


async def update_test_link(db: AsyncSession, tct_id: int, data: dict):
    link = await CompoundTemplateRepository.update_test_link(db, tct_id, data)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vínculo no encontrado.",
        )
    await db.commit()
    await db.refresh(link)
    return link


async def remove_test_from_template(db: AsyncSession, tct_id: int):
    success = await CompoundTemplateRepository.remove_test_link(db, tct_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vínculo no encontrado.",
        )
    await db.commit()
    return {"success": True, "message": "Vínculo eliminado correctamente."}


async def get_templates_for_test(db: AsyncSession, test_id: int):
    return await CompoundTemplateRepository.get_templates_for_test(db, test_id)
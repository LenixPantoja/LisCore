from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.Headquarters.domain.models import Headquarter
from app.domains.masters.domain.models import WorkGroup
from app.domains.studieslab.domain.models import StudiesLab
from app.domains.worksheets.domain.models import WorkSheet
from app.domains.worksheets.infrastructure.repository import WorkSheetRepository


async def _names(db: AsyncSession, sheets: list[WorkSheet]) -> tuple[dict[int, str], dict[int, str]]:
    """Nombres de sede y área para mostrarlos en la lista."""
    hq_ids = {s.ws_headquarter_id for s in sheets if s.ws_headquarter_id}
    wg_ids = {s.ws_work_group_id for s in sheets if s.ws_work_group_id}
    hq = dict((await db.execute(select(Headquarter.id, Headquarter.name).where(Headquarter.id.in_(hq_ids)))).all()) if hq_ids else {}
    wg = dict((await db.execute(select(WorkGroup.wg_id, WorkGroup.wg_name).where(WorkGroup.wg_id.in_(wg_ids)))).all()) if wg_ids else {}
    return hq, wg


def _to_dict(sheet: WorkSheet, hq: dict, wg: dict, study_count: int) -> dict:
    return {
        "ws_id": sheet.ws_id,
        "ws_name": sheet.ws_name,
        "ws_description": sheet.ws_description,
        "ws_headquarter_id": sheet.ws_headquarter_id,
        "ws_work_group_id": sheet.ws_work_group_id,
        "ws_include_free_column": sheet.ws_include_free_column,
        "ws_active": sheet.ws_active,
        "ws_created_at": sheet.ws_created_at,
        "ws_updated_at": sheet.ws_updated_at,
        "headquarter_name": hq.get(sheet.ws_headquarter_id),
        "work_group_name": wg.get(sheet.ws_work_group_id),
        "study_count": study_count,
    }


async def _get_or_404(db: AsyncSession, ws_id: int, with_studies: bool = False) -> WorkSheet:
    sheet = await WorkSheetRepository.get_by_id(db, ws_id, with_studies)
    if not sheet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hoja de trabajo no encontrada.")
    return sheet


async def _commit(db: AsyncSession, action: str) -> None:
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo {action} la hoja de trabajo: verifique la sede, el sector y los estudios.",
        )


async def list_worksheets(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active_only: bool = False,
    work_group_id: Optional[int] = None,
    headquarter_id: Optional[int] = None,
) -> dict:
    sheets, total = await WorkSheetRepository.get_paginated(
        db, skip, limit, search, active_only, work_group_id, headquarter_id
    )
    sheets = list(sheets)
    hq, wg = await _names(db, sheets)
    counts = await WorkSheetRepository.study_counts(db, [s.ws_id for s in sheets])
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [_to_dict(s, hq, wg, counts.get(s.ws_id, 0)) for s in sheets],
    }


async def get_worksheet(db: AsyncSession, ws_id: int) -> dict:
    sheet = await _get_or_404(db, ws_id, with_studies=True)
    hq, wg = await _names(db, [sheet])

    study_ids = [link.wss_study_id for link in sheet.study_links]
    studies = {}
    if study_ids:
        rows = await db.execute(
            select(StudiesLab, WorkGroup.wg_name)
            .outerjoin(WorkGroup, WorkGroup.wg_id == StudiesLab.work_groups_id)
            .where(StudiesLab.id.in_(study_ids))
        )
        studies = {study.id: (study, wg_name) for study, wg_name in rows.all()}

    data = _to_dict(sheet, hq, wg, len(study_ids))
    data["studies"] = [
        {
            "id": link.wss_study_id,
            "code": studies[link.wss_study_id][0].code,
            "name": studies[link.wss_study_id][0].name,
            "cups_code": studies[link.wss_study_id][0].cups_code,
            "work_group_id": studies[link.wss_study_id][0].work_groups_id,
            "work_group_name": studies[link.wss_study_id][1],
            "order": link.wss_order,
        }
        for link in sheet.study_links
        if link.wss_study_id in studies
    ]
    return data


async def create_worksheet(db: AsyncSession, data: dict) -> dict:
    sheet = WorkSheet(**data)
    db.add(sheet)
    await _commit(db, "crear")
    await db.refresh(sheet)
    return await get_worksheet(db, sheet.ws_id)


async def update_worksheet(db: AsyncSession, ws_id: int, data: dict) -> dict:
    sheet = await _get_or_404(db, ws_id)
    for key, value in data.items():
        setattr(sheet, key, value)
    await _commit(db, "actualizar")
    return await get_worksheet(db, ws_id)


async def delete_worksheet(db: AsyncSession, ws_id: int) -> dict:
    sheet = await _get_or_404(db, ws_id)
    await db.delete(sheet)
    await _commit(db, "eliminar")
    return {"detail": "Hoja de trabajo eliminada."}


async def set_worksheet_studies(db: AsyncSession, ws_id: int, study_ids: list[int]) -> dict:
    await _get_or_404(db, ws_id)
    unique_ids = list(dict.fromkeys(study_ids))  # sin repetidos, conservando el orden
    if unique_ids:
        found = set((await db.execute(select(StudiesLab.id).where(StudiesLab.id.in_(unique_ids)))).scalars().all())
        missing = [sid for sid in unique_ids if sid not in found]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estudios inexistentes: {', '.join(map(str, missing))}",
            )
    await WorkSheetRepository.replace_studies(db, ws_id, unique_ids)
    await _commit(db, "actualizar los estudios de")
    db.expire_all()
    return await get_worksheet(db, ws_id)

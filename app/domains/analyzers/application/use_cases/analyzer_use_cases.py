from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.analyzers.infrastructure.repository import AnalyzerRepository
from fastapi import HTTPException, status
from typing import Optional


# ========== ANALYZER GROUPS ==========

async def create_analyzer_group(db: AsyncSession, data: dict):
    """Create a new analyzer group"""
    return await AnalyzerRepository.create_analyzer_group(db, data)

async def list_analyzer_groups(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active: Optional[bool] = None
):
    """List analyzer groups with pagination"""
    items, total = await AnalyzerRepository.get_analyzer_groups(db, skip, limit, search, active)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_analyzer_group_by_id(db: AsyncSession, group_id: int):
    """Get analyzer group by ID"""
    group = await AnalyzerRepository.get_analyzer_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupo de analizador con ID {group_id} no encontrado"
        )
    return group

async def update_analyzer_group(db: AsyncSession, group_id: int, update_data: dict):
    """Update an analyzer group"""
    group = await AnalyzerRepository.update_analyzer_group(db, group_id, update_data)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupo de analizador con ID {group_id} no encontrado"
        )
    return group

async def delete_analyzer_group(db: AsyncSession, group_id: int):
    """Delete an analyzer group"""
    return await AnalyzerRepository.delete_analyzer_group(db, group_id)


# ========== ANALYZERS ==========

async def create_analyzer(db: AsyncSession, data: dict):
    """Create a new analyzer"""
    return await AnalyzerRepository.create_analyzer(db, data)

async def list_analyzers(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active: Optional[bool] = None,
    group_id: Optional[int] = None
):
    """List analyzers with pagination"""
    items, total = await AnalyzerRepository.get_analyzers(db, skip, limit, search, active, group_id)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_analyzer_by_id(db: AsyncSession, analyzer_id: int):
    """Get analyzer by ID"""
    analyzer = await AnalyzerRepository.get_analyzer_by_id(db, analyzer_id)
    if not analyzer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analizador con ID {analyzer_id} no encontrado"
        )
    return analyzer

async def update_analyzer(db: AsyncSession, analyzer_id: int, update_data: dict):
    """Update an analyzer"""
    analyzer = await AnalyzerRepository.update_analyzer(db, analyzer_id, update_data)
    if not analyzer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analizador con ID {analyzer_id} no encontrado"
        )
    return analyzer

async def delete_analyzer(db: AsyncSession, analyzer_id: int):
    """Delete an analyzer"""
    return await AnalyzerRepository.delete_analyzer(db, analyzer_id)


# ========== ANALYZER DETAILS ==========

async def create_analyzer_detail(db: AsyncSession, data: dict):
    """Create a new analyzer detail"""
    return await AnalyzerRepository.create_analyzer_detail(db, data)

async def list_analyzer_details(
    db: AsyncSession,
    analyzer_id: int,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active: Optional[bool] = None
):
    """List analyzer details with pagination"""
    # Verify analyzer exists
    analyzer = await AnalyzerRepository.get_analyzer_by_id(db, analyzer_id)
    if not analyzer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analizador con ID {analyzer_id} no encontrado"
        )

    items, total = await AnalyzerRepository.get_analyzer_details(db, analyzer_id, skip, limit, search, active)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_analyzer_detail_by_id(db: AsyncSession, detail_id: int):
    """Get analyzer detail by ID"""
    detail = await AnalyzerRepository.get_analyzer_detail_by_id(db, detail_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detalle de analizador con ID {detail_id} no encontrado"
        )
    return detail

async def update_analyzer_detail(db: AsyncSession, detail_id: int, update_data: dict):
    """Update an analyzer detail"""
    detail = await AnalyzerRepository.update_analyzer_detail(db, detail_id, update_data)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detalle de analizador con ID {detail_id} no encontrado"
        )
    return detail

async def delete_analyzer_detail(db: AsyncSession, detail_id: int):
    """Delete an analyzer detail"""
    return await AnalyzerRepository.delete_analyzer_detail(db, detail_id)

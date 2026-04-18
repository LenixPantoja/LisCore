from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.domains.laboratories.api.schemas import (
    LaboratoryBulkUpdateItem,
    LaboratoryBulkUpdateResponse,
    InvalidateLaboratoriesRequest,
    InvalidateLaboratoriesResponse,
    ValidateLaboratoriesRequest,
    ValidateLaboratoriesResponse,
    ClearLaboratoryResultsRequest,
    ClearLaboratoryResultsResponse
)
from app.domains.laboratories.application.use_cases import laboratory_use_cases as use_cases

router = APIRouter()

@router.put("/bulk-update", response_model=LaboratoryBulkUpdateResponse, status_code=status.HTTP_200_OK)
async def bulk_update(
    data: List[LaboratoryBulkUpdateItem],
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza múltiples laboratorios a la vez a partir de sus l_id.
    Actualiza l_result, l_result_comp, l_nota_validation y l_user_validation_id de forma selectiva.
    """
    # Convertir cada item de Pydantic a dict excluyendo los campos no enviados (unset)
    data_dicts = [item.model_dump(exclude_unset=True) for item in data]
    return await use_cases.bulk_update_laboratories(db, data_dicts)

@router.post("/invalidate", response_model=InvalidateLaboratoriesResponse, status_code=status.HTTP_200_OK)
async def invalidate_laboratories(
    request: InvalidateLaboratoriesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Desvalida uno o múltiples laboratorios cambiando su estado a 1.
    Solo permite desvalidar cuando el estado actual es >= 2.
    
    Args:
        request: Objeto con lista de laboratory_ids a desvalidar
        
    Returns:
        InvalidateLaboratoriesResponse con detalles de la operación
    """
    return await use_cases.invalidate_laboratories(db, request.laboratory_ids)

@router.post("/validate", response_model=ValidateLaboratoriesResponse, status_code=status.HTTP_200_OK)
async def validate_laboratories(
    request: ValidateLaboratoriesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Valida uno o múltiples laboratorios cambiando su estado a 2.
    
    Args:
        request: Objeto con lista de laboratory_ids a validar
        
    Returns:
        ValidateLaboratoriesResponse con detalles de la operación
    """
    return await use_cases.validate_laboratories(db, request.laboratory_ids)

@router.post("/clear-results", response_model=ClearLaboratoryResultsResponse, status_code=status.HTTP_200_OK)
async def clear_laboratory_results(
    request: ClearLaboratoryResultsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Limpia los resultados de uno o múltiples laboratorios.
    Solo permite limpiar cuando el estado actual es < 2.
    Establece l_result, l_result_num y l_result_comp a NULL.
    
    Args:
        request: Objeto con lista de laboratory_ids a limpiar
        
    Returns:
        ClearLaboratoryResultsResponse con detalles de la operación
    """
    return await use_cases.clear_laboratory_results(db, request.laboratory_ids)

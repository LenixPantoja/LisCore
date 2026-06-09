from fastapi import APIRouter, Depends, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.laboratories.api.schemas import (
    LaboratoryBulkUpdateItem,
    LaboratoryBulkUpdateResponse,
    InvalidateLaboratoriesRequest,
    InvalidateLaboratoriesResponse,
    ValidateLaboratoriesRequest,
    ValidateLaboratoriesResponse,
    ClearLaboratoryResultsRequest,
    ClearLaboratoryResultsResponse,
    UpdateOrderDetailStateRequest,
    UpdateOrderDetailStateResponse,
    GraphicLinkRequest,
    GraphicUploadResponse,
)
from app.domains.laboratories.application.use_cases import laboratory_use_cases as use_cases

router = APIRouter()

@router.put("/bulk-update", response_model=LaboratoryBulkUpdateResponse, status_code=status.HTTP_200_OK,
            dependencies=[Depends(require_permission("Laboratories:BulkUpdate"))])
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

@router.post("/invalidate", response_model=InvalidateLaboratoriesResponse, status_code=status.HTTP_200_OK,
             dependencies=[Depends(require_permission("Laboratories:Invalidate"))])
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
    return await use_cases.invalidate_laboratories(db, request.laboratory_ids, request.usr_id, request.note)

@router.post("/validate", response_model=ValidateLaboratoriesResponse, status_code=status.HTTP_200_OK,
             dependencies=[Depends(require_permission("Laboratories:Validate"))])
async def validate_laboratories(
    request: ValidateLaboratoriesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Valida laboratorios con sus resultados:
    - Si el ítem trae l_result o l_result_comp: registra el resultado y valida (l_state = 2).
    - Si solo trae l_nota_validation: guarda la nota sin validar el laboratorio.
    - Si no trae ninguno de los anteriores: omite el ítem.

    Args:
        request: Objeto con lista de ítems a procesar

    Returns:
        ValidateLaboratoriesResponse con detalles de la operación
    """
    items = [item.model_dump() for item in request.items]
    return await use_cases.validate_laboratories(db, items)

@router.post("/clear-results", response_model=ClearLaboratoryResultsResponse, status_code=status.HTTP_200_OK,
             dependencies=[Depends(require_permission("Laboratories:ClearResults"))])
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


@router.patch(
    "/orders/{order_id}/studies/{study_id}/state",
    response_model=UpdateOrderDetailStateResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("Laboratories:UpdateState"))],
)
async def update_order_detail_state(
    order_id: int,
    study_id: int,
    data: UpdateOrderDetailStateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Cambia el estado de un estudio en OrdersDetails.

    - **0** → Ingresado
    - **1** → Pendiente
    - **2** → Descartado
    """
    return await use_cases.update_order_detail_state(db, order_id, study_id, data.state)


@router.post("/{l_id}/graphic", response_model=GraphicUploadResponse, status_code=status.HTTP_200_OK,
             dependencies=[Depends(require_permission("Laboratories:ManageGraphics"))])
async def upload_laboratory_graphic(
    l_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Sube una imagen al bucket 'graphics' de MinIO y la vincula al resultado gráfico del laboratorio.

    - **l_id**: ID del laboratorio al que se vincula la imagen.
    - **file**: Archivo de imagen (JPG, PNG, etc.).

    Retorna la URL presignada de acceso a la imagen.
    """
    file_data = await file.read()
    return await use_cases.upload_laboratory_graphic(
        db,
        l_id,
        file_data,
        file.filename or "image.jpg",
        file.content_type or "image/jpeg",
    )


@router.post("/{l_id}/graphic/link", response_model=GraphicUploadResponse, status_code=status.HTTP_200_OK,
             dependencies=[Depends(require_permission("Laboratories:ManageGraphics"))])
async def link_laboratory_graphic(
    l_id: int,
    data: GraphicLinkRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Vincula un object_name ya existente en MinIO al l_result_graphic del laboratorio.

    Útil cuando el analizador u otro sistema externo sube la imagen directamente a MinIO
    y notifica al LIS con el nombre del objeto resultante.

    - **l_id**: ID del laboratorio al que se vincula la imagen.
    - **object_name**: Nombre del objeto en el bucket 'graphics'.
    """
    return await use_cases.link_laboratory_graphic(db, l_id, data.object_name)

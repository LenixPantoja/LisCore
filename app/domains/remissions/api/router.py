from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import require_permission, get_current_user
from app.domains.remissions.api.schemas import (
    ExternalLabCreateRequest,
    ExternalLabUpdateRequest,
    ExternalLabResponse,
    ExternalLabListResponse,
    RemissionCreateRequest,
    RemissionResponse,
    RemissionDetailFullResponse,
    RemissionListResponse,
    AddItemsRequest,
    AddItemsByBarcodeRequest,
    AddItemsResponse,
    ShipRemissionRequest,
    ReceiveItemRequest,
    CancelRemissionRequest,
    RemissionCreatedResponse,
    MessageResponse,
)
from app.domains.remissions.application.use_cases import remission_use_cases as use_cases

router = APIRouter()

# ═══════════════════════════════════════════════════════════════════════
#  External Reference Laboratories
# ═══════════════════════════════════════════════════════════════════════

ext_lab_router = APIRouter()


@ext_lab_router.post(
    "",
    response_model=ExternalLabResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear laboratorio de referencia externo",
    dependencies=[Depends(require_permission("Remissions:ManageExternalLabs"))],
)
async def create_external_lab(
    data: ExternalLabCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.create_external_lab(db, data.model_dump())


@ext_lab_router.get(
    "",
    response_model=ExternalLabListResponse,
    summary="Listar laboratorios de referencia externos",
    dependencies=[Depends(require_permission("Remissions:View"))],
)
async def list_external_labs(
    active_only: bool = Query(True, description="Filtrar solo activos"),
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.list_external_labs(db, active_only=active_only)


@ext_lab_router.get(
    "/{erl_id}",
    response_model=ExternalLabResponse,
    summary="Obtener laboratorio externo por ID",
    dependencies=[Depends(require_permission("Remissions:View"))],
)
async def get_external_lab(
    erl_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.get_external_lab(db, erl_id)


@ext_lab_router.put(
    "/{erl_id}",
    response_model=ExternalLabResponse,
    summary="Actualizar laboratorio externo",
    dependencies=[Depends(require_permission("Remissions:ManageExternalLabs"))],
)
async def update_external_lab(
    erl_id: int,
    data: ExternalLabUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.update_external_lab(db, erl_id, data.model_dump(exclude_unset=True))


@ext_lab_router.delete(
    "/{erl_id}",
    response_model=MessageResponse,
    summary="Eliminar laboratorio externo",
    dependencies=[Depends(require_permission("Remissions:ManageExternalLabs"))],
)
async def delete_external_lab(
    erl_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.delete_external_lab(db, erl_id)


# ═══════════════════════════════════════════════════════════════════════
#  Remissions
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "",
    response_model=RemissionCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear remisión (cabecera) en estado Pendiente",
    description="Genera el consecutivo automático con formato REM-<AÑO>-<SEDE_ORIGEN_ID>-<SECUENCIAL>.",
    dependencies=[Depends(require_permission("Remissions:Create"))],
)
async def create_remission(
    data: RemissionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await use_cases.create_remission(
        db,
        rem_type=data.rem_type,
        origin_headquarter_id=data.rem_origin_headquarter_id,
        user_id=current_user.usr_id,
        dest_headquarter_id=data.rem_dest_headquarter_id,
        dest_external_lab_id=data.rem_dest_external_lab_id,
        observations=data.rem_observations,
    )


@router.get(
    "",
    # response_model removed — enriched dict serialized natively
    summary="Listar remisiones",
    description="Filtra por estado, tipo y sede origen. Incluye datos de sedes y usuario.",
    dependencies=[Depends(require_permission("Remissions:View"))],
)
async def list_remissions(
    state: Optional[int] = Query(None, description="Filtrar por estado (1=Pendiente, 2=Enviado, 3=Recibido Completo, 4=Recibido con Novedad, 5=Cancelado)"),
    type_: Optional[str] = Query(None, alias="type", description="Filtrar por tipo: 'LOCAL' o 'EXTERNAL'"),
    origin_hq_id: Optional[int] = Query(None, description="Filtrar por sede origen"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.list_remissions(
        db, state=state, type_=type_, origin_hq_id=origin_hq_id, skip=skip, limit=limit
    )


@router.get(
    "/{rem_id}",
    # response_model removed — enriched dict serialized natively
    summary="Obtener detalle completo de una remisión",
    description="Incluye los ítems del detalle, logs de estado, nombres de sedes y datos del usuario creador.",
    dependencies=[Depends(require_permission("Remissions:View"))],
)
async def get_remission(
    rem_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await use_cases.get_remission(db, rem_id)


@router.post(
    "/{rem_id}/items",
    response_model=AddItemsResponse,
    summary="Agregar ítems al detalle de la remisión",
    description="Agrega un array de pares (so_id, od_id). Solo si la remisión está Pendiente.",
    dependencies=[Depends(require_permission("Remissions:Create"))],
)
async def add_items(
    rem_id: int,
    data: AddItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Convertir cada item Pydantic a dict
    items_dicts = [item.model_dump() for item in data.items]
    return await use_cases.add_items(db, rem_id, items_dicts, current_user.usr_id)


@router.post(
    "/{rem_id}/items/by-barcode",
    response_model=AddItemsResponse,
    summary="Agregar ítems por código de barras de la muestra",
    description="Recibe el código de barras de la muestra (ej: 060600022613). Los primeros 10 dígitos son el número de orden, los siguientes el sufijo. Resuelve automáticamente el SamplesOrder y los OrdersDetails asociados.",
    dependencies=[Depends(require_permission("Remissions:Create"))],
)
async def add_items_by_barcode(
    rem_id: int,
    data: AddItemsByBarcodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await use_cases.add_items_by_barcode(
        db, rem_id, data.sample_barcode, current_user.usr_id
    )


@router.delete(
    "/{rem_id}/items/{detail_id}",
    response_model=MessageResponse,
    summary="Eliminar un ítem de la remisión",
    description="Elimina un ítem del detalle. Solo si la remisión está Pendiente.",
    dependencies=[Depends(require_permission("Remissions:Create"))],
)
async def remove_item(
    rem_id: int,
    detail_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await use_cases.remove_item(db, rem_id, detail_id, current_user.usr_id)


@router.patch(
    "/{rem_id}/ship",
    response_model=MessageResponse,
    summary="Enviar remisión",
    description="Cambia el estado a Enviado (2). Registra transportador y temperatura. Actualiza los OrdersDetails a 'En Tránsito'.",
    dependencies=[Depends(require_permission("Remissions:Ship"))],
)
async def ship_remission(
    rem_id: int,
    data: ShipRemissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await use_cases.ship_remission(
        db, rem_id, current_user.usr_id,
        courier_name=data.rem_courier_name,
        temperature_courier=data.rem_temperature_courier,
    )


@router.patch(
    "/{rem_id}/receive-item",
    response_model=MessageResponse,
    summary="Procesar recepción unitaria de un ítem",
    description="Actualiza el estado de un ítem en el destino. Reevalúa el estado de la cabecera al procesar todos los ítems.",
    dependencies=[Depends(require_permission("Remissions:Receive"))],
)
async def receive_item(
    rem_id: int,
    data: ReceiveItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await use_cases.receive_item(
        db, rem_id, data.remd_id, current_user.usr_id,
        item_state=data.remd_item_state,
        rejection_reason=data.remd_rejection_reason,
    )


@router.patch(
    "/{rem_id}/cancel",
    response_model=MessageResponse,
    summary="Cancelar remisión",
    description="Solo permitido si la remisión está en estado Pendiente.",
    dependencies=[Depends(require_permission("Remissions:Cancel"))],
)
async def cancel_remission(
    rem_id: int,
    data: CancelRemissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await use_cases.cancel_remission(db, rem_id, current_user.usr_id, notes=data.notes)
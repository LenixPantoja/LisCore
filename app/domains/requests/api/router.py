from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.requests.api.schemas import (
    InboundOrderCreate,
    InboundOrderUpdate,
    InboundOrderResponse,
    InboundOrderPaginatedResponse,
    InboundOrderDetailUpdate,
    InboundOrderDetailResponse,
    CreateOrderFromInboundRequest,
    CreateOrderFromInboundResponse,
)
from app.domains.requests.application.use_cases.inbound_order_use_cases import (
    create_inbound_order,
    get_inbound_order,
    list_inbound_orders,
    update_inbound_order,
    delete_inbound_order,
    update_inbound_order_detail,
    create_order_from_inbound,
)

router = APIRouter()


@router.post("/", response_model=InboundOrderResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("Requests:Create"))])
async def create(payload: InboundOrderCreate, db: AsyncSession = Depends(get_db)):
    return await create_inbound_order(db, payload)


@router.get("/", response_model=InboundOrderPaginatedResponse,
            dependencies=[Depends(require_permission("Requests:List"))])
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    states: Optional[List[int]] = Query(
        None,
        description="Filtrar por estado(s) del detalle. Valores: 0=Pendiente, 1=Ejecutada, "
                    "2=Con Resultados, 3=Enviada, 4=Recibida, 5=Con Error",
    ),
    enterprise_id: int = Query(..., description="ID de empresa (requerido)"),
    date_from: Optional[datetime] = Query(None, description="Fecha/hora inicio (io_date_request)"),
    date_to: Optional[datetime] = Query(None, description="Fecha/hora fin (io_date_request)"),
    search: Optional[str] = Query(None, description="Buscar por documento de paciente o número de ingreso"),
    db: AsyncSession = Depends(get_db),
):
    return await list_inbound_orders(
        db,
        page=page,
        page_size=page_size,
        detail_states=states,
        enterprise_id=enterprise_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


@router.get("/{io_id}", response_model=InboundOrderResponse,
            dependencies=[Depends(require_permission("Requests:GetOne"))])
async def get_one(io_id: int, db: AsyncSession = Depends(get_db)):
    return await get_inbound_order(db, io_id)


@router.patch("/{io_id}", response_model=InboundOrderResponse,
              dependencies=[Depends(require_permission("Requests:Update"))])
async def update(io_id: int, payload: InboundOrderUpdate, db: AsyncSession = Depends(get_db)):
    return await update_inbound_order(db, io_id, payload)


@router.delete("/{io_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("Requests:Delete"))])
async def delete(io_id: int, db: AsyncSession = Depends(get_db)):
    await delete_inbound_order(db, io_id)


@router.patch("/details/{iod_id}", response_model=InboundOrderDetailResponse,
              dependencies=[Depends(require_permission("Requests:Update"))])
async def update_detail(
    iod_id: int, payload: InboundOrderDetailUpdate, db: AsyncSession = Depends(get_db)
):
    return await update_inbound_order_detail(db, iod_id, payload)


@router.post(
    "/create-order",
    response_model=CreateOrderFromInboundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una Order desde un InboundOrder",
    description=(
        "Recibe el ID de un InboundOrder y una lista de IDs de InboundOrderDetail. "
        "Crea una Order con los estudios de los detalles seleccionados, actualiza "
        "dichos detalles a estado Ejecutada (1) y guarda el ID de la orden creada."
    ),
    dependencies=[Depends(require_permission("Requests:CreateOrder"))],
)
async def create_order_from_inbound_endpoint(
    payload: CreateOrderFromInboundRequest,
    db: AsyncSession = Depends(get_db),
):
    return await create_order_from_inbound(db, payload)

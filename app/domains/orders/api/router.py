from datetime import date
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import require_permission, get_current_user
from app.domains.users.infrastructure.models import AppUser
from app.domains.orders.api.schemas import (
    OrderCreate, OrderUpdate, OrderResponse, OrderPaginatedResponse, 
    NextOrderNumberResponse, OrderDetailsPaginatedResponse, OrderFullDetailsResponse,
    OrderCreatedResponse, OrderEditRequest, OrderEditResponse,
    GraficoEvolutivoResponse, CancelStudiesRequest, CancelStudiesResponse,
)
from app.domains.orders.application.use_cases import order_use_cases as use_cases

router = APIRouter()

@router.post("/", response_model=OrderCreatedResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("Orders:Create"))])
async def create(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_order(db, data.model_dump())

@router.get("/", response_model=OrderPaginatedResponse,
            dependencies=[Depends(require_permission("Orders:List"))])
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    order_number: Optional[str] = None,
    patient_document: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    order_state: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await use_cases.list_orders(
        db,
        skip,
        limit,
        order_number=order_number,
        patient_document=patient_document,
        start_date=start_date,
        end_date=end_date,
        order_state=order_state,
        search=search
    )

@router.get("/next-number", response_model=NextOrderNumberResponse,
            dependencies=[Depends(require_permission("Orders:GetNextNumber"))])
async def get_next_order_number(db: AsyncSession = Depends(get_db)):
    """
    Get the next order number (last order ID + 1).

    Informative endpoint only - does not create an order.
    """
    return await use_cases.get_next_order_number(db)

@router.get("/grafico-evolutivo/patient/{patient_id}/test/{test_id}", response_model=GraficoEvolutivoResponse,
            dependencies=[Depends(require_permission("Orders:GetEvolutionChart"))])
async def get_grafico_evolutivo(
    patient_id: int,
    test_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Histórico evolutivo de resultados de un examen para un paciente.
    """
    return await use_cases.get_grafico_evolutivo(db, patient_id, test_id)


@router.get("/{id}", response_model=OrderResponse,
            dependencies=[Depends(require_permission("Orders:GetOne"))])
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_order_by_id(db, id)

@router.patch("/{id}", response_model=OrderResponse,
              dependencies=[Depends(require_permission("Orders:Update"))])
async def update(id: int, data: OrderUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_order(db, id, data.model_dump(exclude_unset=True))

@router.put("/{id}", response_model=OrderEditResponse, status_code=status.HTTP_200_OK,
            dependencies=[Depends(require_permission("Orders:Edit"))])
async def edit(
    id: int,
    data: OrderEditRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    """
    Edita campos de una orden y/o agrega nuevos estudios.
    """
    return await use_cases.edit_order(
        db, id, data.model_dump(exclude_unset=True), current_user.usr_id
    )


@router.post("/{id}/cancel-studies", response_model=CancelStudiesResponse, status_code=status.HTTP_200_OK,
             dependencies=[Depends(require_permission("Orders:CancelStudies"))])
async def cancel_studies(id: int, data: CancelStudiesRequest, db: AsyncSession = Depends(get_db)):
    """
    Anula uno o varios estudios de una orden.
    """
    result = await use_cases.cancel_order_studies(db, id, data.study_ids)
    return CancelStudiesResponse(
        success=True,
        o_id=id,
        cancelled_detail_ids=result["cancelled_detail_ids"],
        order_cancelled=result["order_cancelled"],
        message=(
            "Todos los estudios anulados. Orden cancelada."
            if result["order_cancelled"]
            else f"{len(result['cancelled_detail_ids'])} estudio(s) anulado(s)."
        ),
    )

@router.get("/by-number/{o_number}/details", response_model=OrderDetailsPaginatedResponse,
            dependencies=[Depends(require_permission("Orders:GetDetails"))])
async def get_order_details_paginated(
    o_number: str,
    skip_labs: int = Query(0, ge=0),
    limit_labs: int = Query(100, ge=1, le=500),
    skip_tests: int = Query(0, ge=0),
    limit_tests: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get an order by number with its paginated laboratories and tests.
    """
    return await use_cases.get_order_details_paginated_by_number(
        db, o_number, skip_labs, limit_labs, skip_tests, limit_tests
    )

@router.get("/{id}/full", response_model=OrderFullDetailsResponse,
            dependencies=[Depends(require_permission("Orders:GetFullDetails"))])
async def get_full_order_by_id(id: int, db: AsyncSession = Depends(get_db)):
    """
    Get full details of an order including all non-paginated children arrays.
    """
    return await use_cases.get_full_order_details_by_id(db, id)
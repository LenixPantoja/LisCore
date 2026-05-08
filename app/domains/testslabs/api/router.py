from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.database import get_db
from app.domains.testslabs.api.schemas import (
    TestsLabCreate, TestsLabUpdate, TestsLabResponse,
    RangeReferenceCreate, RangeReferenceUpdate,
    RangeReferenceResponse, RangeReferenceListResponse,
    ReferenceValueCreate, ReferenceValueUpdate,
    ReferenceValueResponse, ReferenceValueListResponse,
)
from app.domains.studieslab.api.schemas import TestsLabPaginatedResponse
from app.domains.testslabs.application.use_cases import tests_lab_use_cases as use_cases
from app.domains.testslabs.application.use_cases import ranges_reference_use_cases as rr_use_cases
from app.domains.testslabs.application.use_cases import reference_value_use_cases as rv_use_cases

router = APIRouter()


# --- TestsLab CRUD ---

@router.post("/", response_model=TestsLabResponse, status_code=status.HTTP_201_CREATED)
async def create(data: TestsLabCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_test(db, data.model_dump())

@router.get("/", response_model=TestsLabPaginatedResponse)
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await use_cases.list_tests(db, skip, limit, search)

@router.get("/{id}", response_model=TestsLabResponse)
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_test_by_id(db, id)

@router.patch("/{id}", response_model=TestsLabResponse)
async def update(id: int, data: TestsLabUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_test(db, id, data.model_dump(exclude_unset=True))

@router.delete("/{id}")
async def delete(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.delete_test(db, id)


# --- RangesReferences ---

@router.post(
    "/{test_id}/ranges-references",
    response_model=RangeReferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear rango de referencia",
    description="Asocia un nuevo rango de referencia a una prueba de laboratorio.",
)
async def create_range_reference(
    test_id: int,
    data: RangeReferenceCreate,
    db: AsyncSession = Depends(get_db),
):
    return await rr_use_cases.create_range_reference(db, test_id, data.model_dump())


@router.get(
    "/{test_id}/ranges-references",
    response_model=RangeReferenceListResponse,
    summary="Listar rangos de referencia",
    description="Retorna todos los rangos de referencia asociados a una prueba de laboratorio.",
)
async def list_ranges_references(
    test_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await rr_use_cases.list_ranges_references_by_test(db, test_id)


@router.get(
    "/ranges-references/{range_id}",
    response_model=RangeReferenceResponse,
    summary="Obtener rango de referencia",
)
async def get_range_reference(range_id: int, db: AsyncSession = Depends(get_db)):
    return await rr_use_cases.get_range_reference(db, range_id)


@router.patch(
    "/ranges-references/{range_id}",
    response_model=RangeReferenceResponse,
    summary="Actualizar rango de referencia",
)
async def update_range_reference(
    range_id: int,
    data: RangeReferenceUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await rr_use_cases.update_range_reference(db, range_id, data.model_dump(exclude_unset=True))


@router.delete(
    "/ranges-references/{range_id}",
    summary="Eliminar rango de referencia",
)
async def delete_range_reference(range_id: int, db: AsyncSession = Depends(get_db)):
    return await rr_use_cases.delete_range_reference(db, range_id)


# --- ReferencesValues ---

@router.post(
    "/ranges-references/{ranges_references_id}/reference-values",
    response_model=ReferenceValueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear valor de referencia",
    description="Asocia un nuevo valor de referencia a un rango de referencia.",
)
async def create_reference_value(
    ranges_references_id: int,
    data: ReferenceValueCreate,
    db: AsyncSession = Depends(get_db),
):
    return await rv_use_cases.create_reference_value(db, ranges_references_id, data.model_dump())


@router.get(
    "/ranges-references/{ranges_references_id}/reference-values",
    response_model=ReferenceValueListResponse,
    summary="Listar valores de referencia",
    description="Retorna todos los valores de referencia asociados a un rango de referencia.",
)
async def list_reference_values(
    ranges_references_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await rv_use_cases.list_reference_values_by_range(db, ranges_references_id)


@router.get(
    "/reference-values/{value_id}",
    response_model=ReferenceValueResponse,
    summary="Obtener valor de referencia",
)
async def get_reference_value(value_id: int, db: AsyncSession = Depends(get_db)):
    return await rv_use_cases.get_reference_value(db, value_id)


@router.patch(
    "/reference-values/{value_id}",
    response_model=ReferenceValueResponse,
    summary="Actualizar valor de referencia",
)
async def update_reference_value(
    value_id: int,
    data: ReferenceValueUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await rv_use_cases.update_reference_value(db, value_id, data.model_dump(exclude_unset=True))


@router.delete(
    "/reference-values/{value_id}",
    summary="Eliminar valor de referencia",
)
async def delete_reference_value(value_id: int, db: AsyncSession = Depends(get_db)):
    return await rv_use_cases.delete_reference_value(db, value_id)

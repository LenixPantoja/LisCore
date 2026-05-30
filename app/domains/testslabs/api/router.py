from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.testslabs.api.schemas import (
    TestsLabCreate, TestsLabUpdate, TestsLabResponse,
    RangeReferenceCreate, RangeReferenceUpdate,
    RangeReferenceResponse, RangeReferenceListResponse,
    ReferenceValueCreate, ReferenceValueUpdate,
    ReferenceValueResponse, ReferenceValueListResponse,
)
from app.domains.testslabs.api.format_complete_schemas import (
    FormatCompleteCreate, FormatCompleteUpdate, FormatCompleteResponse, FormatCompleteListResponse,
    TestslabFormatCompleteCreate, TestslabFormatCompleteUpdate,
    TestslabFormatCompleteResponse, TestslabFormatCompleteListResponse,
)
from app.domains.studieslab.api.schemas import TestsLabPaginatedResponse
from app.domains.testslabs.application.use_cases import tests_lab_use_cases as use_cases
from app.domains.testslabs.application.use_cases import ranges_reference_use_cases as rr_use_cases
from app.domains.testslabs.application.use_cases import reference_value_use_cases as rv_use_cases
from app.domains.testslabs.application.use_cases import format_complete_use_cases as fc_use_cases
from app.domains.testslabs.application.use_cases import testslab_format_complete_use_cases as tfc_use_cases

router = APIRouter()


# --- TestsLab CRUD ---

@router.post("/", response_model=TestsLabResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("TestsLab:Create"))])
async def create(data: TestsLabCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_test(db, data.model_dump())

@router.get("/", response_model=TestsLabPaginatedResponse,
            dependencies=[Depends(require_permission("TestsLab:List"))])
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await use_cases.list_tests(db, skip, limit, search)

@router.get("/{id}", response_model=TestsLabResponse,
            dependencies=[Depends(require_permission("TestsLab:GetOne"))])
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_test_by_id(db, id)

@router.patch("/{id}", response_model=TestsLabResponse,
              dependencies=[Depends(require_permission("TestsLab:Update"))])
async def update(id: int, data: TestsLabUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_test(db, id, data.model_dump(exclude_unset=True))

@router.delete("/{id}",
               dependencies=[Depends(require_permission("TestsLab:Delete"))])
async def delete(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.delete_test(db, id)


# --- RangesReferences ---

@router.post(
    "/{test_id}/ranges-references",
    response_model=RangeReferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear rango de referencia",
    description="Asocia un nuevo rango de referencia a una prueba de laboratorio.",
    dependencies=[Depends(require_permission("TestsLab:ManageRanges"))],
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
    dependencies=[Depends(require_permission("TestsLab:ManageRanges"))],
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
    dependencies=[Depends(require_permission("TestsLab:ManageRanges"))],
)
async def get_range_reference(range_id: int, db: AsyncSession = Depends(get_db)):
    return await rr_use_cases.get_range_reference(db, range_id)


@router.patch(
    "/ranges-references/{range_id}",
    response_model=RangeReferenceResponse,
    summary="Actualizar rango de referencia",
    dependencies=[Depends(require_permission("TestsLab:ManageRanges"))],
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
    dependencies=[Depends(require_permission("TestsLab:ManageRanges"))],
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
    dependencies=[Depends(require_permission("TestsLab:ManageReferenceValues"))],
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
    dependencies=[Depends(require_permission("TestsLab:ManageReferenceValues"))],
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
    dependencies=[Depends(require_permission("TestsLab:ManageReferenceValues"))],
)
async def get_reference_value(value_id: int, db: AsyncSession = Depends(get_db)):
    return await rv_use_cases.get_reference_value(db, value_id)


@router.patch(
    "/reference-values/{value_id}",
    response_model=ReferenceValueResponse,
    summary="Actualizar valor de referencia",
    dependencies=[Depends(require_permission("TestsLab:ManageReferenceValues"))],
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
    dependencies=[Depends(require_permission("TestsLab:ManageReferenceValues"))],
)
async def delete_reference_value(value_id: int, db: AsyncSession = Depends(get_db)):
    return await rv_use_cases.delete_reference_value(db, value_id)


# --- FormatComplete CRUD ---

@router.post(
    "/formats-complete",
    response_model=FormatCompleteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear formato de completado",
    tags=["Formats Complete"],
    dependencies=[Depends(require_permission("TestsLab:ManageFormats"))],
)
async def create_format(data: FormatCompleteCreate, db: AsyncSession = Depends(get_db)):
    return await fc_use_cases.create_format(db, data.model_dump())


@router.get(
    "/formats-complete",
    response_model=FormatCompleteListResponse,
    summary="Listar formatos de completado",
    tags=["Formats Complete"],
    dependencies=[Depends(require_permission("TestsLab:ManageFormats"))],
)
async def list_formats(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await fc_use_cases.list_formats(db, skip, limit, search)


@router.get(
    "/formats-complete/{fc_id}",
    response_model=FormatCompleteResponse,
    summary="Obtener formato de completado",
    tags=["Formats Complete"],
    dependencies=[Depends(require_permission("TestsLab:ManageFormats"))],
)
async def get_format(fc_id: int, db: AsyncSession = Depends(get_db)):
    return await fc_use_cases.get_format_by_id(db, fc_id)


@router.patch(
    "/formats-complete/{fc_id}",
    response_model=FormatCompleteResponse,
    summary="Actualizar formato de completado",
    tags=["Formats Complete"],
    dependencies=[Depends(require_permission("TestsLab:ManageFormats"))],
)
async def update_format(fc_id: int, data: FormatCompleteUpdate, db: AsyncSession = Depends(get_db)):
    return await fc_use_cases.update_format(db, fc_id, data.model_dump(exclude_unset=True))


@router.delete(
    "/formats-complete/{fc_id}",
    summary="Eliminar formato de completado",
    tags=["Formats Complete"],
    dependencies=[Depends(require_permission("TestsLab:ManageFormats"))],
)
async def delete_format(fc_id: int, db: AsyncSession = Depends(get_db)):
    return await fc_use_cases.delete_format(db, fc_id)


# --- Testslab ↔ FormatComplete (vínculos) ---

@router.post(
    "/{test_id}/formats-complete",
    response_model=TestslabFormatCompleteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Vincular formato a una prueba",
    tags=["Formats Complete"],
    dependencies=[Depends(require_permission("TestsLab:ManageFormats"))],
)
async def link_format(
    test_id: int,
    data: TestslabFormatCompleteCreate,
    db: AsyncSession = Depends(get_db),
):
    return await tfc_use_cases.link_format_to_testslab(db, test_id, data.model_dump())


@router.get(
    "/{test_id}/formats-complete",
    response_model=TestslabFormatCompleteListResponse,
    summary="Listar formatos vinculados a una prueba",
    tags=["Formats Complete"],
    dependencies=[Depends(require_permission("TestsLab:ManageFormats"))],
)
async def list_formats_by_test(test_id: int, db: AsyncSession = Depends(get_db)):
    return await tfc_use_cases.list_formats_by_testslab(db, test_id)


@router.patch(
    "/formats-complete-link/{tfc_id}",
    response_model=TestslabFormatCompleteResponse,
    summary="Actualizar vínculo formato-prueba",
    tags=["Formats Complete"],
    dependencies=[Depends(require_permission("TestsLab:ManageFormats"))],
)
async def update_link(
    tfc_id: int,
    data: TestslabFormatCompleteUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await tfc_use_cases.update_link(db, tfc_id, data.model_dump(exclude_unset=True))


@router.delete(
    "/formats-complete-link/{tfc_id}",
    summary="Desvincular formato de una prueba",
    tags=["Formats Complete"],
    dependencies=[Depends(require_permission("TestsLab:ManageFormats"))],
)
async def unlink_format(tfc_id: int, db: AsyncSession = Depends(get_db)):
    return await tfc_use_cases.unlink_format_from_testslab(db, tfc_id)


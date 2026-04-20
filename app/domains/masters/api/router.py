from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.masters.api.schemas import (
    CountryResponse, CountryPaginatedResponse,
    DepartmentResponse, DepartmentPaginatedResponse,
    CityResponse, CityPaginatedResponse,
    DocumentTypeResponse, SexTypeResponse,
    AfiliationTypeResponse, RegimeResponse, ServiceResponse, ServicePaginatedResponse, TypeLiabilityResponse, ClassificationResponse,
    TechniqueCreate, TechniqueUpdate, TechniqueResponse, WorkGroupCreate, WorkGroupUpdate, WorkGroupResponse,
    ReferralLocationCreate, ReferralLocationUpdate, ReferralLocationResponse,
    DiagnosisResponse, DiagnosisPaginatedResponse, SchoolingResponse
)
from app.domains.masters.application.use_cases import (
    get_countries, get_departments_by_country, get_cities_by_department, get_document_types,
    get_sex_types, get_afiliation_types, get_regimes, get_services, get_type_liabilities,
    get_classifications, masters_crud_use_cases as crud
)
from app.domains.masters.infrastructure.repository import MastersRepository
from app.domains.masters.domain.models import Technique, WorkGroup, ReferralLocation, Diagnosis, Schooling, City

router = APIRouter()

@router.get("/countries", response_model=CountryPaginatedResponse)
async def read_countries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para obtener la lista de países con paginación.
    """
    items, total = await MastersRepository.get_countries_paginated(db, skip, limit, search, active)
    return {"total": total, "skip": skip, "limit": limit, "items": items}

@router.get("/departments", response_model=DepartmentPaginatedResponse)
async def read_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    country_id: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para obtener departamentos con paginación.
    """
    items, total = await MastersRepository.get_departments_paginated(db, country_id, skip, limit, search)
    return {"total": total, "skip": skip, "limit": limit, "items": items}

@router.get("/cities", response_model=CityPaginatedResponse)
async def read_cities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para obtener ciudades con paginación.
    """
    items, total = await MastersRepository.get_cities_paginated(db, department_id, skip, limit, search)
    return {"total": total, "skip": skip, "limit": limit, "items": items}

@router.get("/cities/{city_id}", response_model=CityResponse)
async def read_city(city_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener una ciudad por su ID.
    """
    return await crud.get_item_by_id(db, City, city_id)

@router.get("/document-types", response_model=List[DocumentTypeResponse])
async def read_document_types(db: AsyncSession = Depends(get_db)):
    return await get_document_types.execute(db)

@router.get("/sex-types", response_model=List[SexTypeResponse])
async def read_sex_types(db: AsyncSession = Depends(get_db)):
    return await get_sex_types.execute(db)

@router.get("/afiliation-types", response_model=List[AfiliationTypeResponse])
async def read_afiliation_types(db: AsyncSession = Depends(get_db)):
    return await get_afiliation_types.execute(db)

@router.get("/regimes", response_model=List[RegimeResponse])
async def read_regimes(db: AsyncSession = Depends(get_db)):
    return await get_regimes.execute(db)

@router.get("/services", response_model=ServicePaginatedResponse)
async def read_services(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para obtener la lista de servicios con paginación.
    """
    items, total = await MastersRepository.get_services_paginated(db, skip, limit, search, active)
    return {"total": total, "skip": skip, "limit": limit, "items": items}

@router.get("/type-liabilities", response_model=List[TypeLiabilityResponse])
async def read_type_liabilities(db: AsyncSession = Depends(get_db)):
    return await get_type_liabilities.execute(db)

@router.get("/classifications", response_model=List[ClassificationResponse])
async def read_classifications(db: AsyncSession = Depends(get_db)):
    return await get_classifications.execute(db)

# --- Techniques ---
@router.post("/techniques", response_model=TechniqueResponse)
async def create_technique(data: TechniqueCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_item(db, Technique, data.model_dump())

@router.get("/techniques", response_model=List[TechniqueResponse])
async def read_techniques(db: AsyncSession = Depends(get_db)):
    return await crud.get_items(db, Technique)

@router.patch("/techniques/{id}", response_model=TechniqueResponse)
async def update_technique(id: int, data: TechniqueUpdate, db: AsyncSession = Depends(get_db)):
    return await crud.update_item(db, Technique, id, data.model_dump(exclude_unset=True))

# --- Work Groups ---
@router.post("/work-groups", response_model=WorkGroupResponse)
async def create_work_group(data: WorkGroupCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_item(db, WorkGroup, data.model_dump())

@router.get("/work-groups", response_model=List[WorkGroupResponse])
async def read_work_groups(db: AsyncSession = Depends(get_db)):
    return await crud.get_items(db, WorkGroup)

@router.patch("/work-groups/{id}", response_model=WorkGroupResponse)
async def update_work_group(id: int, data: WorkGroupUpdate, db: AsyncSession = Depends(get_db)):
    # En Work_groups la PK es wg_id, pero nuestro crud genérico usa db.get(model, id)
    # Si el modelo tiene una PK distinta a 'id', debemos manejarlo.
    # Para WorkGroup, asumimos que db.get funciona correctamente con wg_id mapeado como primary_key.
    return await crud.update_item(db, WorkGroup, id, data.model_dump(exclude_unset=True))

# --- Referral Locations ---
@router.post("/referral-locations", response_model=ReferralLocationResponse)
async def create_referral_location(data: ReferralLocationCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_item(db, ReferralLocation, data.model_dump())

@router.get("/referral-locations", response_model=List[ReferralLocationResponse])
async def read_referral_locations(db: AsyncSession = Depends(get_db)):
    return await crud.get_items(db, ReferralLocation)

@router.patch("/referral-locations/{id}", response_model=ReferralLocationResponse)
async def update_referral_location(id: int, data: ReferralLocationUpdate, db: AsyncSession = Depends(get_db)):
    return await crud.update_item(db, ReferralLocation, id, data.model_dump(exclude_unset=True))

# --- Diagnoses ---
@router.get("/diagnoses", response_model=DiagnosisPaginatedResponse)
async def read_diagnoses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    code: Optional[str] = None,
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para obtener la lista de diagnósticos con paginación.
    """
    items, total = await MastersRepository.get_diagnoses_paginated(db, skip, limit, code, description, search)
    return {"total": total, "skip": skip, "limit": limit, "items": items}

@router.get("/diagnoses/{id}", response_model=DiagnosisResponse)
async def read_diagnosis(id: int, db: AsyncSession = Depends(get_db)):
    return await crud.get_item_by_id(db, Diagnosis, id)

# --- Schooling ---
@router.get("/schooling", response_model=List[SchoolingResponse])
async def read_schoolings(db: AsyncSession = Depends(get_db)):
    return await crud.get_items(db, Schooling)

@router.get("/schooling/{id}", response_model=SchoolingResponse)
async def read_schooling(id: int, db: AsyncSession = Depends(get_db)):
    return await crud.get_item_by_id(db, Schooling, id)
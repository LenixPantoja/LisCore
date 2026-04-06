from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.masters.api.schemas import (
    CountryResponse, DepartmentResponse, CityResponse, DocumentTypeResponse, SexTypeResponse, 
    AfiliationTypeResponse, RegimeResponse, ServiceResponse, TypeLiabilityResponse, ClassificationResponse,
    TechniqueCreate, TechniqueUpdate, TechniqueResponse, WorkGroupCreate, WorkGroupUpdate, WorkGroupResponse,
    ReferralLocationCreate, ReferralLocationUpdate, ReferralLocationResponse,
    DiagnosisResponse, SchoolingResponse
)
from app.domains.masters.application.use_cases import (
    get_countries, get_departments_by_country, get_cities_by_department, get_document_types, 
    get_sex_types, get_afiliation_types, get_regimes, get_services, get_type_liabilities, 
    get_classifications, masters_crud_use_cases as crud
)
from app.domains.masters.domain.models import Technique, WorkGroup, ReferralLocation, Diagnosis, Schooling

router = APIRouter()

@router.get("/countries", response_model=List[CountryResponse])
async def read_countries(db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener la lista de todos los países activos.
    """
    return await get_countries.execute(db)

@router.get("/countries/{country_id}/departments", response_model=List[DepartmentResponse])
async def read_departments_by_country(country_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener todos los departamentos de un país dado su ID.
    """
    departments = await get_departments_by_country.execute(db, country_id)
    if not departments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Departments not found for this country")
    return departments

@router.get("/departments/{department_id}/cities", response_model=List[CityResponse])
async def read_cities_by_department(department_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener todas las ciudades de un departamento dado su ID.
    """
    cities = await get_cities_by_department.execute(db, department_id)
    if not cities:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cities not found for this department")
    return cities

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

@router.get("/services", response_model=List[ServiceResponse])
async def read_services(db: AsyncSession = Depends(get_db)):
    return await get_services.execute(db)

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
@router.get("/diagnoses", response_model=List[DiagnosisResponse])
async def read_diagnoses(
    skip: int = 0, 
    limit: int = 100, 
    code: Optional[str] = None, 
    description: Optional[str] = None, 
    db: AsyncSession = Depends(get_db)
):
    return await crud.get_diagnoses_paginated(db, skip, limit, code, description)

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
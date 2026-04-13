from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.domains.patients.api.schemas import PatientCreate, PatientUpdate, PatientResponse, PatientWithAgeResponse
from app.domains.patients.application.use_cases import patient_use_cases as use_cases

router = APIRouter()

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create(data: PatientCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_patient(db, data.model_dump())

@router.get("/", response_model=List[PatientResponse])
async def list_all(db: AsyncSession = Depends(get_db)):
    return await use_cases.list_patients(db)

@router.get("/document/{doc_number}", response_model=PatientWithAgeResponse)
async def get_by_document(doc_number: str, db: AsyncSession = Depends(get_db)):
    """
    Get a patient by document number with calculated age.
    """
    result = await use_cases.get_patient_by_document(db, doc_number)
    patient_data = result["patient"]
    age_info = result["pt_age"]

    return {
        "pt_id": patient_data.pt_id,
        "pt_Number_document": patient_data.pt_Number_document,
        "pt_firts_name": patient_data.pt_firts_name,
        "pt_middle_name": patient_data.pt_middle_name,
        "pt_last_name": patient_data.pt_last_name,
        "pt_second_last_name": patient_data.pt_second_last_name,
        "pt_sex_type": patient_data.pt_sex_type,
        "pt_phone_number": patient_data.pt_phone_number,
        "pt_mail": patient_data.pt_mail,
        "pt_address": patient_data.pt_address,
        "pt_date_of_birth": patient_data.pt_date_of_birth,
        "pt_authorize_habeas_data": patient_data.pt_authorize_habeas_data,
        "pt_afiliation_type": patient_data.pt_afiliation_type,
        "pt_enterprise_id": patient_data.pt_enterprise_id,
        "pt_Document_Type_id": patient_data.pt_Document_Type_id,
        "pt_city_id": patient_data.pt_city_id,
        "pt_created_at": patient_data.pt_created_at,
        "pt_updated_at": patient_data.pt_updated_at,
        "pt_age": age_info
    }

@router.get("/{id}", response_model=PatientResponse)
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_patient_by_id(db, id)

@router.patch("/{id}", response_model=PatientResponse)
async def update(id: int, data: PatientUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_patient(db, id, data.model_dump(exclude_unset=True))
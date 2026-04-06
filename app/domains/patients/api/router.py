from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.domains.patients.api.schemas import PatientCreate, PatientUpdate, PatientResponse
from app.domains.patients.application.use_cases import patient_use_cases as use_cases

router = APIRouter()

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create(data: PatientCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_patient(db, data.model_dump())

@router.get("/", response_model=List[PatientResponse])
async def list_all(db: AsyncSession = Depends(get_db)):
    return await use_cases.list_patients(db)

@router.get("/{id}", response_model=PatientResponse)
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_patient_by_id(db, id)

@router.patch("/{id}", response_model=PatientResponse)
async def update(id: int, data: PatientUpdate, db: AsyncSession = Depends(get_db)):
    return await use_cases.update_patient(db, id, data.model_dump(exclude_unset=True))
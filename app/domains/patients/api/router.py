# domains/patients/api/router.py

from fastapi import APIRouter, Depends
from .schemas import PatientCreate
from app.domains.patients.application.use_cases.create_patient import execute

router = APIRouter()

@router.post("/")
async def create_patient(data: PatientCreate):
    return await execute(data)
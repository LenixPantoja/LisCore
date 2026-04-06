from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.patients.infrastructure.repository import PatientRepository
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

async def create_patient(db: AsyncSession, data: dict):
    try:
        # Validar si ya existe el documento
        existing = await PatientRepository.get_by_document(db, data.get("pt_Number_document"))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El número de documento ya se encuentra registrado."
            )
        return await PatientRepository.create(db, data)
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig)
        if "pt_sex_type" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El tipo de sexo especificado no es válido.")
        if "pt_afiliation_type" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El tipo de afiliación no es válido.")
        if "pt_enterprise_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La empresa especificada no existe.")
        if "pt_Document_Type_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El tipo de documento no es válido.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error de integridad al guardar el paciente.")

async def list_patients(db: AsyncSession):
    return await PatientRepository.get_all(db)

async def get_patient_by_id(db: AsyncSession, pt_id: int):
    patient = await PatientRepository.get_by_id(db, pt_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return patient

async def update_patient(db: AsyncSession, pt_id: int, data: dict):
    try:
        patient = await PatientRepository.update(db, pt_id, data)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
        return patient
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error al actualizar datos del paciente.")
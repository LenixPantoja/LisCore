from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.domains.patients.domain.models import Patient

class PatientRepository:
    @staticmethod
    async def create(db: AsyncSession, data: dict) -> Patient:
        new_patient = Patient(**data)
        db.add(new_patient)
        await db.commit()
        await db.refresh(new_patient)
        return new_patient

    @staticmethod
    async def get_all(db: AsyncSession) -> List[Patient]:
        result = await db.execute(
            select(Patient).options(
                selectinload(Patient.sex_type),
                selectinload(Patient.afiliation),
                selectinload(Patient.enterprise),
                selectinload(Patient.document_type),
                selectinload(Patient.city)
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, pt_id: int) -> Optional[Patient]:
        result = await db.execute(
            select(Patient).filter(Patient.pt_id == pt_id).options(
                selectinload(Patient.sex_type),
                selectinload(Patient.afiliation),
                selectinload(Patient.enterprise),
                selectinload(Patient.document_type),
                selectinload(Patient.city)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, pt_id: int, update_data: dict) -> Optional[Patient]:
        patient = await db.get(Patient, pt_id)
        if patient:
            for key, value in update_data.items():
                setattr(patient, key, value)
            await db.commit()
            await db.refresh(patient)
        return patient

    @staticmethod
    async def get_by_document(db: AsyncSession, doc_number: str) -> Optional[Patient]:
        result = await db.execute(select(Patient).filter(Patient.pt_Number_document == doc_number))
        return result.scalars().first()
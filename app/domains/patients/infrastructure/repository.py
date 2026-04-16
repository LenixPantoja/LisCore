from typing import List, Optional, Tuple
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
    async def get_paginated(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None) -> Tuple[List[Patient], int]:
        """Obtener pacientes con paginación y búsqueda opcional."""
        from sqlalchemy import func
        
        query = select(Patient).options(
            selectinload(Patient.sex_type),
            selectinload(Patient.afiliation),
            selectinload(Patient.enterprise),
            selectinload(Patient.document_type),
            selectinload(Patient.city)
        )
        
        # Aplicar filtro de búsqueda si se proporciona
        if search:
            search_filter = (
                Patient.pt_Number_document.ilike(f"%{search}%") |
                Patient.pt_firts_name.ilike(f"%{search}%") |
                Patient.pt_last_name.ilike(f"%{search}%") |
                Patient.pt_mail.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        
        # Obtener el total usando count
        count_query = select(func.count()).select_from(Patient)
        if search:
            count_query = count_query.where(search_filter)
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Aplicar paginación
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()
        
        return items, total

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
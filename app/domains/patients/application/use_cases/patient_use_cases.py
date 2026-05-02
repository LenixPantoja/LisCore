from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.patients.infrastructure.repository import PatientRepository
from app.domains.patients.domain.rules import calculate_age
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

async def list_patients(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None):
    """Listar pacientes con paginación y búsqueda."""
    items, total = await PatientRepository.get_paginated(db, skip, limit, search)
    for patient in items:
        patient.pt_age = calculate_age(patient.pt_date_of_birth) if patient.pt_date_of_birth else {"years": 0, "months": 0, "days": 0}
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

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

async def get_patient_by_document(db: AsyncSession, doc_number: str):
    """Get a patient by document number with calculated age"""
    patient = await PatientRepository.get_by_document(db, doc_number)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    patient.pt_age = calculate_age(patient.pt_date_of_birth) if patient.pt_date_of_birth else {"years": 0, "months": 0, "days": 0}
    return patient

async def get_patient_orders_with_details(db: AsyncSession, search_query: str, skip: int = 0, limit: int = 100):
    from app.domains.orders.infrastructure.repository import OrderRepository
    
    orders, total = await OrderRepository.get_patient_orders_paginated(db, search_query, skip, limit)
    
    state_mapping = {
        1: "Ingresada",
        2: "Pendiente",
        3: "Con Resultados",
        4: "Anulada",
        5: "Cerrada"
    }
    
    items = []
    for order in orders:
        # Construir nombre completo amigable
        parts = [order.patient.pt_firts_name, order.patient.pt_middle_name, order.patient.pt_last_name, order.patient.pt_second_last_name]
        full_name = " ".join([p for p in parts if p])
        
        items.append({
            "o_id": order.o_id,
            "pt_Number_document": order.patient.pt_Number_document,
            "pt_Document_Type_id": order.patient.pt_Document_Type_id,
            "o_number": order.o_number,
            "o_date": order.o_date,
            "patient_full_name": full_name,
            "o_order_state": order.o_order_state,
            "order_state_name": state_mapping.get(order.o_order_state, "Desconocido")
        })
        
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }
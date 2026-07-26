from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.patients.infrastructure.repository import PatientRepository
from app.domains.patients.domain.rules import calculate_age
from app.domains.patients.domain.models import Patient
from app.domains.traces.constants import OPERATION_EDIT_DEMOGRAPHICS
from app.domains.traces.models import AppTrace
from app.domains.app_results_page.application.use_cases.app_results_page_use_cases import provision_for_patient
from app.core.security import get_password_hash
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError


async def create_patient(db: AsyncSession, data: dict, user_id: int | None = None):
    try:
        # Validar si ya existe el documento
        existing = await PatientRepository.get_by_document(db, data.get("pt_Number_document"))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El número de documento ya se encuentra registrado."
            )

        # Password por defecto: el número de documento, siempre hasheada
        raw_password = data.get("pt_password") or data.get("pt_Number_document")
        data["pt_password"] = get_password_hash(raw_password)

        patient = await PatientRepository.create(db, data)
        await provision_for_patient(db, patient)

        if user_id:
            db.add(AppTrace(
                usr_id=user_id,
                operation_type=OPERATION_EDIT_DEMOGRAPHICS,
                operation_description=f"Creación de paciente {patient.pt_Number_document}",
                notes=f"Paciente: {patient.pt_firts_name} {patient.pt_last_name} | Documento: {patient.pt_Number_document}",
            ))
            await db.commit()

        return patient
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

async def update_patient(db: AsyncSession, pt_id: int, data: dict, user_id: int | None = None):
    """
    Update patient fields and register trace with before/after diff.
    """
    try:
        editable_fields = [
            "pt_Number_document", "pt_firts_name", "pt_middle_name",
            "pt_last_name", "pt_second_last_name", "pt_phone_number",
            "pt_mail", "pt_address", "pt_date_of_birth", "pt_sex_type",
            "pt_authorize_habeas_data", "pt_afiliation_type",
            "pt_enterprise_id", "pt_Document_Type_id", "pt_city_id",
        ]

        field_labels = {
            "pt_Number_document": "Documento",
            "pt_firts_name": "Primer nombre",
            "pt_middle_name": "Segundo nombre",
            "pt_last_name": "Primer apellido",
            "pt_second_last_name": "Segundo apellido",
            "pt_phone_number": "Teléfono",
            "pt_mail": "Email",
            "pt_address": "Dirección",
            "pt_date_of_birth": "Fecha de nacimiento",
            "pt_sex_type": "Sexo",
            "pt_authorize_habeas_data": "Habeas Data",
            "pt_afiliation_type": "Afiliación",
            "pt_enterprise_id": "Empresa",
            "pt_Document_Type_id": "Tipo documento",
            "pt_city_id": "Ciudad",
        }

        # --- Snapshot BEFORE ---
        patient = await PatientRepository.get_by_id(db, pt_id)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

        before_snapshot = {
            field: getattr(patient, field, None)
            for field in editable_fields
        }

        # Si se envía una nueva contraseña, hashearla antes de guardar
        if data.get("pt_password"):
            data["pt_password"] = get_password_hash(data["pt_password"])

        # --- Perform update ---
        updated = await PatientRepository.update(db, pt_id, data)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

        # --- Build diff ---
        diff_parts: list[str] = []
        for field in editable_fields:
            if field in data and data[field] is not None:
                label = field_labels.get(field, field)
                old_val = before_snapshot.get(field)
                new_val = data[field]
                if old_val != new_val:
                    diff_parts.append(f"{label}: {old_val} → {new_val}")

        # --- Register trace ---
        if diff_parts and user_id:
            db.add(AppTrace(
                usr_id=user_id,
                operation_type=OPERATION_EDIT_DEMOGRAPHICS,
                operation_description=f"Actualización datos paciente {updated.pt_Number_document}",
                notes=" | ".join(diff_parts),
            ))
            await db.commit()

        return updated

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
    from app.domains.orders.domain.constants import ORDER_STATES

    orders, total = await OrderRepository.get_patient_orders_paginated(db, search_query, skip, limit)

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
            "order_state_name": ORDER_STATES.get(order.o_order_state, "Desconocido")
        })
        
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }
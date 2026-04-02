# application/use_cases/create_patient.py

from app.domains.patients.infrastructure.repository import PatientRepository
from app.messaging.producer import publish_event

async def execute(data):
    patient = await PatientRepository.create(data)

    await publish_event("patient_created", {"id": patient.id})

    return patient
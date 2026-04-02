from pydantic import BaseModel
from typing import Optional

class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    document_number: str
    # Agrega aquí más campos según lo que necesite tu paciente

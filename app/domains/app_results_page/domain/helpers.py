from datetime import date
from typing import Optional

from app.domains.patients.domain.rules import calculate_age
from app.shared.utils.range_evaluator import SEX_TYPE_IDS_FEMALE, SEX_TYPE_IDS_MALE


def full_name(patient) -> str:
    if not patient:
        return "—"
    parts = [
        patient.pt_firts_name,
        patient.pt_middle_name or "",
        patient.pt_last_name,
        patient.pt_second_last_name or "",
    ]
    return " ".join(p for p in parts if p).strip()


def resolve_sex(patient) -> Optional[str]:
    if not patient or patient.pt_sex_type is None:
        return None
    if patient.pt_sex_type in SEX_TYPE_IDS_FEMALE:
        return "Femenino"
    if patient.pt_sex_type in SEX_TYPE_IDS_MALE:
        return "Masculino"
    return None


def bucket_age_label(dob: Optional[date]) -> Optional[str]:
    """Recién nacido → días, pediátrico (< 1 año) → meses, adulto → años."""
    if not dob:
        return None
    parts = calculate_age(dob)
    if parts["years"] == 0 and parts["months"] == 0:
        n = parts["days"]
        return f"{n} día" if n == 1 else f"{n} días"
    if parts["years"] == 0:
        n = parts["months"]
        return f"{n} mes" if n == 1 else f"{n} meses"
    n = parts["years"]
    return f"{n} año" if n == 1 else f"{n} años"

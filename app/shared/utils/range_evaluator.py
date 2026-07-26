"""
Utilidad para evaluar el rango de referencia de un resultado de laboratorio.

Dado un test_id, el resultado numérico del laboratorio y el paciente (fecha de
nacimiento y género), determina en qué rango de referencia (NORMAL, ACEPTABLE,
CRITICO) se encuentra el valor. El min/max devueltos son siempre los del rango
NORMAL aplicable (por género/edad) — es decir, el valor de referencia a
mostrar, independientemente de en qué rango haya caído el resultado real.
"""

from datetime import date
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.testslabs.domain.models import RangeReference, ReferenceValue
from app.domains.testslabs.domain.constants import (
    AGE_TYPE_DIAS,
    AGE_TYPE_MESES,
    AGE_TYPE_ANIOS,
    RANGE_TYPE_NORMAL,
)


# ── Constantes de género ──────────────────────────────────────────────────────
# Valores que puede tomar RangeReference.gender
GENDER_BOTH = "AMBOS"
GENDER_MALE = "MASCULINO"
GENDER_FEMALE = "FEMENINO"

# IDs de SexType en el LIS que corresponden a Masculino/Femenino
# (usados también fuera de este módulo, p.ej. en pdf_generator, para
# resolver el género visible del paciente a partir de pt_sex_type)
SEX_TYPE_IDS_MALE: set[int] = {1}   # id=1 → Hombre
SEX_TYPE_IDS_FEMALE: set[int] = {3}  # id=3 → Mujer


def _patient_age_in_days(dob: date) -> int:
    """Retorna la edad del paciente en días completos."""
    today = date.today()
    return (today - dob).days


def _patient_age_in_months(dob: date) -> int:
    """Retorna la edad del paciente en meses completos."""
    today = date.today()
    months = (today.year - dob.year) * 12 + (today.month - dob.month)
    if today.day < dob.day:
        months -= 1
    return max(months, 0)


def _patient_age_in_years(dob: date) -> int:
    """Retorna la edad del paciente en años completos."""
    today = date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return max(years, 0)


def _get_patient_age(dob: date, age_type: str) -> int:
    """
    Calcula la edad del paciente en la unidad indicada por age_type.
    age_type: 'DIAS' | 'MESES' | 'AÑOS'
    """
    if age_type == AGE_TYPE_DIAS:
        return _patient_age_in_days(dob)
    if age_type == AGE_TYPE_MESES:
        return _patient_age_in_months(dob)
    return _patient_age_in_years(dob)


def _gender_matches(range_gender: Optional[str], patient_sex_type_id: Optional[int]) -> bool:
    """
    Determina si el género del rango aplica al paciente.
    - AMBOS o None → siempre aplica.
    - MASCULINO → solo si el sex_type del paciente es masculino.
    - FEMENINO → solo si el sex_type del paciente es femenino.
    """
    if not range_gender or range_gender.upper() == GENDER_BOTH:
        return True
    if range_gender.upper() == GENDER_MALE:
        return patient_sex_type_id in SEX_TYPE_IDS_MALE
    if range_gender.upper() == GENDER_FEMALE:
        return patient_sex_type_id in SEX_TYPE_IDS_FEMALE
    return False


def _age_matches(
    range_ref: RangeReference,
    dob: Optional[date],
) -> bool:
    """
    Determina si la edad del paciente está dentro del rango de edad del RangeReference.
    Si no hay fecha de nacimiento, acepta rangos sin restricción de edad.
    """
    has_age_limits = range_ref.min_age is not None or range_ref.max_age is not None
    if not has_age_limits:
        return True
    if dob is None:
        # Sin fecha de nacimiento no podemos validar rangos con límites de edad
        return False
    age = _get_patient_age(dob, range_ref.age_type or AGE_TYPE_ANIOS)
    if range_ref.min_age is not None and age < range_ref.min_age:
        return False
    if range_ref.max_age is not None and age > range_ref.max_age:
        return False
    return True


def _value_in_reference(
    result_num: Optional[Decimal],
    result_text: Optional[str],
    ref_value: ReferenceValue,
) -> bool:
    """
    Verifica si el resultado cae dentro del valor de referencia.

    - Si hay result_num (resultado numérico):
        * Si tiene min_value y max_values → rango numérico inclusivo.
        * Si solo min_value → result >= min.
        * Si solo max_values → result <= max.
    - Si hay result_text (resultado textual):
        * Compara exactamente con text_value del ReferenceValue (case-insensitive).
    """
    # Evaluación numérica
    if result_num is not None:
        if ref_value.min_value is None and ref_value.max_values is None:
            return False
        if ref_value.min_value is not None and ref_value.max_values is not None:
            return Decimal(str(ref_value.min_value)) <= result_num <= Decimal(str(ref_value.max_values))
        if ref_value.min_value is not None:
            return result_num >= Decimal(str(ref_value.min_value))
        if ref_value.max_values is not None:
            return result_num <= Decimal(str(ref_value.max_values))
        return False

    # Evaluación textual
    if result_text is not None and ref_value.text_value is not None:
        return result_text.strip().lower() == str(ref_value.text_value).strip().lower()

    return False


async def evaluate_reference_range(
    db: AsyncSession,
    test_id: int,
    result_num: Optional[float],
    patient_dob: Optional[date],
    patient_sex_type_id: Optional[int],
    result_text: Optional[str] = None,
) -> Tuple[Optional[str], Optional[Decimal], Optional[Decimal]]:
    """
    Evalúa el resultado de un laboratorio contra los rangos de referencia
    configurados para el examen (test_id).

    - result_num: valor numérico (para tests de tipo N).
    - result_text: valor textual (para tests de tipo T).

    Retorna una tupla:
        (range_type, min_value, max_value)

    - range_type: 'NORMAL' | 'ACEPTABLE' | 'CRITICO' | None → el rango en el
      que cae el resultado real.
    - min_value / max_value: límites del rango NORMAL aplicable por
      género/edad (el valor de referencia a mostrar), NO los del rango en el
      que cayó el resultado. None si no hay un rango NORMAL configurado que
      aplique, o para evaluaciones textuales.

    Si no hay resultado evaluable o no se encuentra rango aplicable,
    retorna (None, None, None).

    NOTE: Para evaluar múltiples resultados en un solo request, usar
    `bulk_fetch_ranges` + `evaluate_reference_range_sync` para evitar N+1 queries.
    """
    if result_num is None and not result_text:
        return (None, None, None)

    # Cargar rangos del test ordenados por prioridad ascendente (1 = más prioritario)
    stmt = (
        select(RangeReference)
        .where(RangeReference.test_id == test_id)
        .options(selectinload(RangeReference.reference_values))
        .order_by(RangeReference.priority.asc())
    )
    result = await db.execute(stmt)
    ranges: list[RangeReference] = list(result.scalars().all())

    return evaluate_reference_range_sync(ranges, result_num, patient_dob, patient_sex_type_id, result_text)


async def bulk_fetch_ranges(
    db: AsyncSession,
    test_ids: list[int],
) -> dict[int, list[RangeReference]]:
    """
    Carga todos los RangeReference (con sus ReferenceValues) para múltiples
    test_ids en una sola consulta batch.

    Retorna un dict: {test_id: [RangeReference ordenados por priority asc]}.
    Usar junto con `evaluate_reference_range_sync` para evitar N+1 queries.
    """
    if not test_ids:
        return {}

    stmt = (
        select(RangeReference)
        .where(RangeReference.test_id.in_(test_ids))
        .options(selectinload(RangeReference.reference_values))
        .order_by(RangeReference.test_id, RangeReference.priority.asc())
    )
    result = await db.execute(stmt)
    lookup: dict[int, list[RangeReference]] = {}
    for r in result.scalars().all():
        lookup.setdefault(r.test_id, []).append(r)
    return lookup


def evaluate_reference_range_sync(
    ranges: list[RangeReference],
    result_num: Optional[float],
    patient_dob: Optional[date],
    patient_sex_type_id: Optional[int],
    result_text: Optional[str] = None,
) -> Tuple[Optional[str], Optional[Decimal], Optional[Decimal]]:
    """
    Evaluación pura en memoria usando rangos ya cargados (sin queries DB).
    Usar con los datos obtenidos por `bulk_fetch_ranges`.

    El range_type se determina por el rango en el que cae el resultado real
    (NORMAL/ACEPTABLE/CRITICO, por prioridad). El min/max devuelto es siempre
    el del rango NORMAL aplicable por género/edad — el "valor de referencia"
    a mostrar — sin importar en qué rango haya caído el resultado.
    """
    if result_num is None and not result_text:
        return (None, None, None)

    result_decimal = Decimal(str(result_num)) if result_num is not None else None

    range_type: Optional[str] = None
    normal_min: Optional[Decimal] = None
    normal_max: Optional[Decimal] = None

    for range_ref in ranges:
        if not _gender_matches(range_ref.gender, patient_sex_type_id):
            continue
        if not _age_matches(range_ref, patient_dob):
            continue

        # Capturar los límites del rango NORMAL aplicable, independiente de
        # si el resultado cae ahí o no.
        if normal_min is None and normal_max is None and range_ref.range_type == RANGE_TYPE_NORMAL:
            for ref_val in range_ref.reference_values:
                if ref_val.min_value is not None or ref_val.max_values is not None:
                    normal_min = Decimal(str(ref_val.min_value)) if ref_val.min_value is not None else None
                    normal_max = Decimal(str(ref_val.max_values)) if ref_val.max_values is not None else None
                    break

        # Determinar en qué rango cae el resultado real (primero por prioridad).
        if range_type is None:
            for ref_val in range_ref.reference_values:
                if _value_in_reference(result_decimal, result_text, ref_val):
                    range_type = range_ref.range_type
                    break

    return (range_type, normal_min, normal_max)


def list_reference_values_for_patient(
    ranges: list[RangeReference],
    patient_dob: Optional[date],
    patient_sex_type_id: Optional[int],
) -> list[dict]:
    """
    Devuelve la lista plana de valores de referencia configurados para un
    test que aplican a este paciente por género/edad (uno por cada
    ReferenceValue, sin importar el range_type) — para mostrar todos los
    rangos configurados (NORMAL, ACEPTABLE, CRITICO, etc.), no solo el que
    coincidió con el resultado.
    """
    entries: list[dict] = []
    for range_ref in ranges:
        if not _gender_matches(range_ref.gender, patient_sex_type_id):
            continue
        if not _age_matches(range_ref, patient_dob):
            continue
        for ref_val in range_ref.reference_values:
            entries.append({
                "range_type": range_ref.range_type,
                "gender": range_ref.gender,
                "age_type": range_ref.age_type,
                "min_age": range_ref.min_age,
                "max_age": range_ref.max_age,
                "min_value": float(ref_val.min_value) if ref_val.min_value is not None else None,
                "max_value": float(ref_val.max_values) if ref_val.max_values is not None else None,
                "text_value": ref_val.text_value,
            })
    return entries

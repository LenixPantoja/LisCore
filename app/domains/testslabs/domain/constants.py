"""
Constants for the testslabs domain.
"""

# Range types for RangesReferences
RANGE_TYPE_NORMAL = "NORMAL"
RANGE_TYPE_ACEPTABLE = "ACEPTABLE"
RANGE_TYPE_CRITICO = "CRITICO"

RANGE_TYPES: list[str] = [
    RANGE_TYPE_NORMAL,
    RANGE_TYPE_ACEPTABLE,
    RANGE_TYPE_CRITICO,
]

# Age types for RangesReferences
AGE_TYPE_DIAS = "DIAS"
AGE_TYPE_MESES = "MESES"
AGE_TYPE_ANIOS = "AÑOS"

AGE_TYPES: list[str] = [
    AGE_TYPE_DIAS,
    AGE_TYPE_MESES,
    AGE_TYPE_ANIOS,
]

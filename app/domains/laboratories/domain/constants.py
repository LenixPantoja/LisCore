"""
Constantes del dominio de laboratorios.
"""

# Estados de un resultado de Laboratorio
LABORATORY_STATES: dict[int, str] = {
    0: "Sin Resultados",
    1: "Pendiente",
    2: "Con Resultados",
    3: "Validada",
    4: "Laboratorio Impreso",
}

LABORATORY_STATE_SIN_RESULTADOS = 0
LABORATORY_STATE_PENDIENTE = 1
LABORATORY_STATE_CON_RESULTADOS = 2
LABORATORY_STATE_VALIDADA = 3
LABORATORY_STATE_IMPRESO = 4

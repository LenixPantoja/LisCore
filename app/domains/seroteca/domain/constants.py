"""
Constantes del dominio de seroteca / tracking de muestras.
"""

# Estados de un evento de SamplesLog (log_state)
SAMPLE_LOG_STATES: dict[int, str] = {
    0: "Recibida",
    1: "En proceso",
    2: "Almacenada",
    3: "Retirada",
    4: "Descartada",
}

SAMPLE_LOG_STATE_RECIBIDA = 0
SAMPLE_LOG_STATE_EN_PROCESO = 1
SAMPLE_LOG_STATE_ALMACENADA = 2
SAMPLE_LOG_STATE_RETIRADA = 3
SAMPLE_LOG_STATE_DESCARTADA = 4

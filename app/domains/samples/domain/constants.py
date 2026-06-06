"""
Constantes del dominio de muestras.
"""

# Estados de SamplesOrder (Muestra de una Orden)
SAMPLE_ORDER_STATES: dict[int, str] = {
    0: "Muestra No Ingresada",
    1: "Con Muestra",
    2: "Muestra Sin Definir",
    3: "Almacenada",
}

SAMPLE_ORDER_STATE_NO_INGRESADA = 0
SAMPLE_ORDER_STATE_CON_MUESTRA = 1
SAMPLE_ORDER_STATE_SIN_DEFINIR = 2
SAMPLE_ORDER_STATE_ALMACENADA = 3

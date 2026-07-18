"""
Constantes del dominio de órdenes.
"""

# Estados de una Orden
ORDER_STATES: dict[int, str] = {
    1: "Ingresada",
    2: "Pendiente",
    3: "Con Resultados",
    4: "Validada",
    5: "Impresa",
    6: "Cerrada",
    7: "Anulada",
}

ORDER_STATE_INGRESADA = 1
ORDER_STATE_PENDIENTE = 2
ORDER_STATE_CON_RESULTADOS = 3
ORDER_STATE_VALIDADA = 4
ORDER_STATE_IMPRESA = 5
ORDER_STATE_CERRADA = 6
ORDER_STATE_ANULADA = 7

# Estados de OrdersDetail (Estudio dentro de una Orden)
ORDER_DETAIL_STATES: dict[int, str] = {
    0: "Ingresado",
    1: "Pendiente",
    2: "Descartado",
}

ORDER_DETAIL_STATE_INGRESADO = 0
ORDER_DETAIL_STATE_PENDIENTE = 1
ORDER_DETAIL_STATE_DESCARTADO = 2

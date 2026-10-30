"""
Constantes del dominio de solicitudes entrantes (InboundOrders).
"""

# Estados de un detalle de solicitud entrante (InboundOrderDetail)
INBOUND_ORDER_DETAIL_STATES: dict[int, str] = {
    0: "Pendiente",
    1: "Ejecutada",
    2: "Con Resultados",
    3: "Enviada",
    4: "Recibida",
    5: "Con Error",
}

INBOUND_ORDER_DETAIL_STATE_PENDIENTE = 0
INBOUND_ORDER_DETAIL_STATE_EJECUTADA = 1
INBOUND_ORDER_DETAIL_STATE_CON_RESULTADOS = 2
INBOUND_ORDER_DETAIL_STATE_ENVIADA = 3
INBOUND_ORDER_DETAIL_STATE_RECIBIDA = 4
INBOUND_ORDER_DETAIL_STATE_CON_ERROR = 5

# Prefijo que /api/DinamicaFT/Laboratorio/RegistrarSolicitud antepone al
# IDOrigen en InboundOrder.io_origin (ej. "FT-1"), para identificar al crear la
# orden que la solicitud llegó por esa ruta.
INBOUND_ORIGIN_PREFIX_DINAMICA_FT = "FT-"

"""
Estados del módulo de Remisiones.
"""

# Estados de la cabecera de remisión (rem_state)
REMISSION_STATE_PENDING = 1      # Pendiente — en creación
REMISSION_STATE_SHIPPED = 2      # Enviado / En Ruta
REMISSION_STATE_RECEIVED_OK = 3  # Recibido Completo
REMISSION_STATE_RECEIVED_WITH_NOVELTY = 4  # Recibido con Novedad
REMISSION_STATE_CANCELLED = 5    # Cancelado

# Estados de los ítems del detalle (remd_item_state)
DETAIL_ITEM_STATE_LOADED = 1      # Cargado
DETAIL_ITEM_STATE_RECEIVED_OK = 2 # Recibido Conforme
DETAIL_ITEM_STATE_REJECTED = 3    # Rechazado en Destino

# Estados internos de OrdersDetails después del envío/rechazo
ORDER_DETAIL_STATE_IN_TRANSIT = 90  # Código para "Remitido / Muestra en Tránsito"
ORDER_DETAIL_STATE_REJECTED = 91    # Código para "Muestra Rechazada"
ORDER_DETAIL_STATE_PENDING_RESAMPLE = 1  # "Pendiente Toma de Muestra"
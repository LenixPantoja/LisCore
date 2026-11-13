"""
Constantes del módulo de Alarmas y Críticos.
"""

# Niveles (de más a menos grave)
LEVEL_PANICO = "PANICO"     # riesgo vital: avisar al médico de inmediato
LEVEL_CRITICO = "CRITICO"   # muy alterado: avisar en el turno
LEVEL_DELTA = "DELTA"       # cambio brusco frente al resultado anterior del paciente

LEVELS = (LEVEL_PANICO, LEVEL_CRITICO, LEVEL_DELTA)
LEVEL_RANK = {LEVEL_PANICO: 3, LEVEL_CRITICO: 2, LEVEL_DELTA: 1}
LEVEL_LABEL = {LEVEL_PANICO: "PÁNICO", LEVEL_CRITICO: "CRÍTICO", LEVEL_DELTA: "DELTA"}

# Estados de una alarma
STATE_NUEVA = "NUEVA"            # detectada, falta avisar al médico
STATE_NOTIFICADA = "NOTIFICADA"  # se avisó al médico
STATE_ACUSADA = "ACUSADA"        # el médico confirmó que la recibió
STATE_ESCALADA = "ESCALADA"      # pasó el tiempo meta sin avisar, o se escaló a mano
STATE_CERRADA = "CERRADA"

STATES = (STATE_NUEVA, STATE_NOTIFICADA, STATE_ACUSADA, STATE_ESCALADA, STATE_CERRADA)
PENDING_STATES = (STATE_NUEVA, STATE_ESCALADA)   # pendientes de notificar

# Tipos de evento de la trazabilidad
EV_DETECTADA = "DETECTADA"
EV_NOTIFICADA = "NOTIFICADA"
EV_ACUSADA = "ACUSADA"
EV_ESCALADA = "ESCALADA"
EV_CERRADA = "CERRADA"
EV_NOTA = "NOTA"
EV_CAMBIO = "CAMBIO_VALOR"
EV_REABIERTA = "REABIERTA"
EV_EMPEORO = "EMPEORO"          # subió de nivel (p.ej. crítico → pánico) sin haberse notificado

# Eventos que disparan el aviso emergente / sonoro
NOTICE_EVENTS = (EV_DETECTADA, EV_REABIERTA, EV_EMPEORO)

# Canales de notificación
CHANNELS = ("LLAMADA", "WHATSAPP", "CORREO", "PRESENCIAL")
CHANNEL_LABEL = {"LLAMADA": "Llamada", "WHATSAPP": "WhatsApp", "CORREO": "Correo", "PRESENCIAL": "Presencial"}

SYSTEM_USER = "Sistema"

GENDERS = ("AMBOS", "MASCULINO", "FEMENINO")
AGE_TYPES = ("DIAS", "MESES", "AÑOS")

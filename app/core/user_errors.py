"""
Mensajes de error para el usuario final.

El detalle técnico (excepción, SQL, servicio externo) se escribe en el log del
servidor para soporte; al usuario solo le llega un mensaje claro, sin nombres
de tablas, scripts, servicios ni trazas.
"""
import logging

logger = logging.getLogger("liscore.errors")

SUPPORT_HINT = "Intente de nuevo; si el problema continúa, comuníquese con soporte."


def user_error(message: str, exc: BaseException | None = None) -> str:
    """Registra `exc` en el log y devuelve `message` listo para mostrar."""
    if exc is not None:
        logger.error("%s | %s: %s", message, type(exc).__name__, exc, exc_info=exc)
    message = message.rstrip(". ")
    return f"{message}. {SUPPORT_HINT}"


def not_available(feature: str, technical: str) -> str:
    """Función aún no habilitada en esta instalación (falta configuración del servidor)."""
    logger.warning("%s no disponible: %s", feature, technical)
    return f"{feature} no está disponible en este momento. Comuníquese con el administrador del sistema."

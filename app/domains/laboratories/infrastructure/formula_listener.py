"""
Escucha notificaciones de Postgres (canal `lab_result_changed`) emitidas por
el trigger `trg_notify_lab_result_change` sobre la tabla Laboratories
(ver migrations/037_add_lab_result_notify_trigger.py), y recalcula las
pruebas basadas en fórmula de la orden afectada.

Esto cubre el caso en que un resultado se escribe directamente en la base de
datos (p.ej. una interfaz de transmisión externa que hace UPDATE directo a
Laboratories), sin pasar por la API de este backend — que es el único otro
lugar donde se dispara el recálculo (LaboratoryRepository.bulk_update).

Requiere una conexión asyncpg dedicada (separada del pool de SQLAlchemy) que
vive durante todo el ciclo de vida de la aplicación; se abre/cierra desde
app/lifespan.py.
"""
import logging

import asyncpg

from app.core.config import settings
from app.core.database import async_session
from app.domains.laboratories.infrastructure.repository import LaboratoryRepository

logger = logging.getLogger(__name__)

_CHANNEL = "lab_result_changed"
_listener_conn: asyncpg.Connection | None = None


async def _handle_notification(connection, pid, channel, payload: str) -> None:
    try:
        order_id = int(payload)
    except (TypeError, ValueError):
        logger.warning("Notificación '%s' con payload inválido: %r", _CHANNEL, payload)
        return

    try:
        async with async_session() as db:
            await LaboratoryRepository.recalculate_formula_labs(db, [order_id])
            await db.commit()
    except Exception:
        logger.exception(
            "Error recalculando fórmulas para la orden %s tras notificación externa.", order_id
        )


async def start_listener() -> None:
    """Abre una conexión asyncpg dedicada y se suscribe al canal de notificación."""
    global _listener_conn
    try:
        # Se pasan como argumentos separados (no como DSN concatenado) para que
        # contraseñas con caracteres especiales (p.ej. '#', '@', ':') no rompan
        # el parseo de URL — asyncpg.connect(dsn) sí lo requeriría escapado.
        _listener_conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=int(settings.DB_PORT),
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
        )
        await _listener_conn.add_listener(_CHANNEL, _handle_notification)
        logger.info("Escuchando notificaciones de Postgres en el canal '%s'.", _CHANNEL)
    except Exception:
        logger.exception(
            "No se pudo iniciar el listener de '%s'. El recálculo de fórmulas para "
            "resultados escritos directamente en la base de datos no estará activo.",
            _CHANNEL,
        )
        _listener_conn = None


async def stop_listener() -> None:
    global _listener_conn
    if _listener_conn is not None:
        try:
            await _listener_conn.remove_listener(_CHANNEL, _handle_notification)
        finally:
            await _listener_conn.close()
            _listener_conn = None

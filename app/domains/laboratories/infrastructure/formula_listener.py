"""
Recalcula las pruebas de fórmula cuando un resultado se escribe directamente en
la base de datos (p.ej. la interfaz de los analizadores hace UPDATE directo a
Laboratories), sin pasar por la API de este backend — que es el único otro
lugar donde se dispara el recálculo (LaboratoryRepository.bulk_update).

Dos mecanismos, para que no dependa de una sola conexión:

1. Escucha: notificaciones de Postgres (canal `lab_result_changed`) emitidas
   por el trigger `trg_notify_lab_result_change` sobre Laboratories (ver
   migrations/037_add_lab_result_notify_trigger.py). Recalcula al instante la
   orden afectada.
2. Vigilancia: cada SWEEP_INTERVAL_SECONDS revisa que la conexión de escucha
   siga viva (si se cayó, p.ej. por un corte de red, se reconecta) y hace un
   barrido de las órdenes con resultados de los últimos SWEEP_RECENT_MINUTES
   que tengan fórmulas sin calcular. Al arrancar y tras cada reconexión el
   barrido cubre los últimos SWEEP_LOOKBACK_DAYS días, para ponerse al día con
   lo que llegó mientras no se escuchaba.

Con varios workers de uvicorn, cada uno escucha; el barrido lo hace uno solo a
la vez gracias a un advisory lock.
"""
import asyncio
import logging
from datetime import timedelta

import asyncpg
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session
from app.domains.laboratories.infrastructure.repository import LaboratoryRepository
from app.domains.alarms.infrastructure import detector as alarm_detector
from utils.timezone import get_bogota_now

logger = logging.getLogger(__name__)

_CHANNEL = "lab_result_changed"
SWEEP_INTERVAL_SECONDS = 60
SWEEP_RECENT_MINUTES = 15
SWEEP_LOOKBACK_DAYS = 3

_listener_conn: asyncpg.Connection | None = None
_supervisor_task: asyncio.Task | None = None

# Órdenes recientes con alguna fórmula sin resultado (no validada) y al menos
# un resultado registrado desde :since (la interfaz marca l_date_transmited;
# la API, l_updated_at).
_PENDING_FORMULA_ORDERS_SQL = text("""
    SELECT DISTINCT od.od_order_id
    FROM "Laboratories" fl
    JOIN "TestsLab" ft ON ft.id = fl.l_test_id AND ft.is_formula IS TRUE
    JOIN "OrdersDetails" od ON od.od_id = fl.l_order_detail_id
    JOIN "Orders" o ON o.o_id = od.od_order_id
    WHERE o.o_created_at >= :lookback
      AND (fl.l_result IS NULL OR btrim(fl.l_result) = '')
      AND COALESCE(fl.l_state, 0) < 3
      AND EXISTS (
          SELECT 1
          FROM "Laboratories" il
          JOIN "OrdersDetails" iod ON iod.od_id = il.l_order_detail_id
          WHERE iod.od_order_id = od.od_order_id
            AND il.l_result IS NOT NULL
            AND il.l_id <> fl.l_id
            AND GREATEST(il.l_date_transmited, il.l_updated_at) >= :since
      )
""")


async def _recalculate(order_ids: list[int]) -> None:
    async with async_session() as db:
        await LaboratoryRepository.recalculate_formula_labs(db, order_ids)
        await db.commit()


async def _handle_notification(connection, pid, channel, payload: str) -> None:
    try:
        order_id = int(payload)
    except (TypeError, ValueError):
        logger.warning("Notificación '%s' con payload inválido: %r", _CHANNEL, payload)
        return

    try:
        await _recalculate([order_id])
    except Exception:
        logger.exception(
            "Error recalculando fórmulas para la orden %s tras notificación externa.", order_id
        )

    # Alarmas y Críticos: revisar al instante los resultados de la orden
    # (después de las fórmulas, para incluir los valores calculados).
    try:
        async with async_session() as db:
            await alarm_detector.evaluate(db, order_ids=[order_id])
            await db.commit()
    except Exception:
        logger.exception("Error revisando valores críticos de la orden %s.", order_id)


async def _connect_listener() -> None:
    """Abre la conexión dedicada de escucha (si no está abierta)."""
    global _listener_conn
    if _listener_conn is not None and not _listener_conn.is_closed():
        return
    _listener_conn = None
    # Se pasan como argumentos separados (no como DSN concatenado) para que
    # contraseñas con caracteres especiales (p.ej. '#', '@', ':') no rompan
    # el parseo de URL — asyncpg.connect(dsn) sí lo requeriría escapado.
    conn = await asyncpg.connect(
        host=settings.DB_HOST.strip(),
        port=int(settings.DB_PORT),
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        server_settings={"application_name": "liscore_formula_listener"},
    )
    await conn.add_listener(_CHANNEL, _handle_notification)
    _listener_conn = conn
    logger.info("Escuchando notificaciones de Postgres en el canal '%s'.", _CHANNEL)


async def sweep_pending_formulas(full: bool = False) -> int:
    """
    Calcula las fórmulas pendientes de las órdenes con resultados recientes
    (full=True: de los últimos SWEEP_LOOKBACK_DAYS días). Lo hace un solo
    worker a la vez (advisory lock de transacción). Retorna cuántas órdenes revisó.
    """
    now = get_bogota_now().replace(tzinfo=None)
    lookback = now - timedelta(days=SWEEP_LOOKBACK_DAYS)
    since = lookback if full else now - timedelta(minutes=SWEEP_RECENT_MINUTES)
    async with async_session() as db:
        got_lock = (await db.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtext('formula_sweep'))")
        )).scalar()
        if not got_lock:
            return 0
        order_ids = list((await db.execute(
            _PENDING_FORMULA_ORDERS_SQL, {"lookback": lookback, "since": since}
        )).scalars().all())
        if order_ids:
            await LaboratoryRepository.recalculate_formula_labs(db, order_ids)
        await db.commit()
        return len(order_ids)


async def sweep_alarms(full: bool = False) -> None:
    """
    Alarmas y Críticos: revisa los resultados recientes (o los de las últimas
    CATCH_UP_HOURS al arrancar), escala las alarmas que superaron su tiempo meta
    y cierra las que quedaron sin resultado. Lo hace un solo worker a la vez.
    """
    now = get_bogota_now().replace(tzinfo=None)
    since = now - (timedelta(hours=alarm_detector.CATCH_UP_HOURS) if full
                   else timedelta(minutes=SWEEP_RECENT_MINUTES))
    async with async_session() as db:
        if not await alarm_detector.alarms_ready(db):
            return
        got_lock = (await db.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtext('alarm_sweep'))")
        )).scalar()
        if not got_lock:
            return
        await alarm_detector.evaluate(db, since=since)
        await alarm_detector.close_orphans(db)
        await alarm_detector.escalate_overdue(db)
        await db.commit()


async def _supervise() -> None:
    """Mantiene viva la escucha y hace el barrido periódico."""
    catch_up = True  # al arrancar: ponerse al día con todo lo reciente
    while True:
        try:
            was_listening = _listener_conn is not None and not _listener_conn.is_closed()
            await _connect_listener()
            if not was_listening:
                catch_up = True
        except Exception:
            logger.exception("No se pudo conectar la escucha de '%s'; se reintenta.", _CHANNEL)
        formulas_ok = alarms_ok = False
        try:
            await sweep_pending_formulas(full=catch_up)
            formulas_ok = True
        except Exception:
            logger.exception("Error en el barrido de fórmulas pendientes.")
        try:
            await sweep_alarms(full=catch_up)
            alarms_ok = True
        except Exception:
            logger.exception("Error en el barrido de alarmas y críticos.")
        if formulas_ok and alarms_ok:
            catch_up = False
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)


async def start_listener() -> None:
    """Inicia la escucha y su vigilancia en segundo plano (no bloquea el arranque)."""
    global _supervisor_task
    if _supervisor_task is None or _supervisor_task.done():
        _supervisor_task = asyncio.create_task(_supervise())


async def stop_listener() -> None:
    global _listener_conn, _supervisor_task
    if _supervisor_task is not None:
        _supervisor_task.cancel()
        try:
            await _supervisor_task
        except (asyncio.CancelledError, Exception):
            pass
        _supervisor_task = None
    if _listener_conn is not None:
        try:
            if not _listener_conn.is_closed():
                await _listener_conn.remove_listener(_CHANNEL, _handle_notification)
                await _listener_conn.close()
        finally:
            _listener_conn = None

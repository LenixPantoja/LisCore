import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

LOG_DIR = Path("logs")
SQL_LOG_FILE = LOG_DIR / "sql_queries.log"


def setup_sql_logging() -> None:
    """Escribe cada query SQL (con sus parámetros) en logs/sql_queries.log.

    Controlado por SQL_LOG_ENABLED en .env — apagado por defecto porque
    loguear cada query tiene costo y no debe quedar prendido en producción.
    """
    if not settings.SQL_LOG_ENABLED:
        return

    LOG_DIR.mkdir(exist_ok=True)

    handler = RotatingFileHandler(
        SQL_LOG_FILE, maxBytes=20 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))

    sql_logger = logging.getLogger("sqlalchemy.engine")
    sql_logger.setLevel(logging.INFO)
    sql_logger.addHandler(handler)
    sql_logger.propagate = False

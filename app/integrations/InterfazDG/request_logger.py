"""
Log diario de las solicitudes crudas recibidas por la InterfazDG
(/api/Dinamica/Laboratorio/RegistrarSolicitud).

Cada request se agrega al archivo del día, con nombre
logs/Solicitudes{DDMMYYYY}.log (ej. Solicitudes30092026.log), independiente
de si luego el XML se pudo parsear/registrar o no — así queda registro de
lo que el HIS efectivamente envió para poder depurar cualquier caso.
"""
import logging
from pathlib import Path

from utils.timezone import get_bogota_now

LOG_DIR = Path("logs")

logger = logging.getLogger(__name__)


def _decode_raw_body(raw_body: bytes) -> str:
    """
    Decodifica el cuerpo crudo a texto para dejarlo legible en el log.

    El HIS envía el XML en UTF-16 (con BOM); se detecta el BOM para elegir
    el encoding correcto y, si de todos modos falla, se cae a UTF-8 y por
    último a latin-1 reemplazando los caracteres que no se puedan decodificar,
    para que el log nunca se pierda por un problema de encoding.
    """
    if raw_body.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw_body.decode("utf-16")
        except UnicodeDecodeError:
            pass
    try:
        return raw_body.decode("utf-8")
    except UnicodeDecodeError:
        return raw_body.decode("latin-1", errors="replace")


def log_solicitud_request(raw_body: bytes) -> None:
    """
    Agrega el cuerpo crudo recibido al log diario de solicitudes.

    No lanza excepciones: un fallo al escribir el log nunca debe impedir que
    la solicitud se siga procesando normalmente.
    """
    try:
        LOG_DIR.mkdir(exist_ok=True)
        now = get_bogota_now()
        filename = f"Solicitudes{now.strftime('%d%m%Y')}.log"
        log_path = LOG_DIR / filename

        body_text = _decode_raw_body(raw_body) if raw_body else "(cuerpo vacío)"
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 80}\n[{timestamp}]\n{body_text}\n")
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo escribir el log diario de solicitudes InterfazDG.")

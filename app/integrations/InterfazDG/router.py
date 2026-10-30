"""
Router de la InterfazDG.

Expone los endpoints para recibir solicitudes de exámenes de laboratorio
en formato XML desde el HIS y responde con el acuse de recibido:

- router    -> /api/Dinamica/Laboratorio/RegistrarSolicitud
- router_ft -> /api/DinamicaFT/Laboratorio/RegistrarSolicitud

Ambos reciben el mismo XML (DocumentElement) y comparten el procesamiento;
solo cambia el archivo de log diario donde se guarda lo recibido.
"""
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.integrations.InterfazDG.service import InterfazDGService
from app.integrations.InterfazDG.use_cases import (
    OPCIONES_DINAMICA_FT,
    OpcionesInterfazDG,
    registrar_solicitud_dg,
)
from app.integrations.InterfazDG.request_logger import log_solicitud_request

router = APIRouter()
router_ft = APIRouter()
_service = InterfazDGService()

_ENDPOINT_DOC = dict(
    summary="Recibir solicitud de exámenes de laboratorio (XML)",
    description=(
        "Recibe el XML de solicitud de exámenes enviado por el HIS en formato "
        "InterfazDG (DocumentElement, UTF-8 o UTF-16). Parsea el XML, registra el "
        "InboundOrder con sus detalles y responde con un XML de acuse de recibido "
        "(MensajeResultado)."
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"content": {"application/xml": {}}, "description": "Acuse de recibido XML"},
        422: {"content": {"application/xml": {}}, "description": "XML inválido o datos incompletos"},
    },
)


def _build_acuse(exito: bool, mensaje: str, mensaje_interno: str = "") -> str:
    """
    Construye el XML de acuse de recibido según la especificación InterfazDG.

    Ejemplo de respuesta::

        <?xml version="1.0" encoding="utf-16"?>
        <MensajeResultado>
          <Exito>true</Exito>
          <Mensaje>Solicitud recibida correctamente.</Mensaje>
          <MensajeInterno></MensajeInterno>
        </MensajeResultado>
    """
    root = ET.Element("MensajeResultado")
    ET.SubElement(root, "Exito").text = "true" if exito else "false"
    ET.SubElement(root, "Mensaje").text = mensaje
    ET.SubElement(root, "MensajeInterno").text = mensaje_interno
    return '<?xml version="1.0" encoding="utf-16"?>\n' + ET.tostring(root, encoding="unicode")


@router.post("/RegistrarSolicitud", **_ENDPOINT_DOC)
async def recibir_solicitud(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    return await _procesar_solicitud(request, db, log_prefix="Solicitudes")


@router_ft.post("/RegistrarSolicitud", **_ENDPOINT_DOC)
async def recibir_solicitud_ft(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    # Reglas propias de DinamicaFT: servicio por GEECODIGO, tipo de documento
    # por dt_id_dinamica y Pasto como ciudad por defecto (ver OPCIONES_DINAMICA_FT)
    return await _procesar_solicitud(request, db, log_prefix="SolicitudesFT", opciones=OPCIONES_DINAMICA_FT)


async def _procesar_solicitud(
    request: Request,
    db: AsyncSession,
    log_prefix: str,
    opciones: OpcionesInterfazDG = OpcionesInterfazDG(),
) -> Response:
    raw_body = await request.body()

    # Se guarda lo recibido tal cual, sin importar si luego se puede parsear
    # o registrar correctamente — queda en logs/{log_prefix}{DDMMYYYY}.log.
    log_solicitud_request(raw_body, prefix=log_prefix)

    if not raw_body:
        acuse = _build_acuse(
            exito=False,
            mensaje="El cuerpo de la solicitud está vacío.",
            mensaje_interno="Empty request body.",
        )
        return Response(content=acuse, media_type="application/xml", status_code=400)

    # 1. Parsear el XML
    try:
        solicitud = _service.receive_solicitud(raw_body)
    except ET.ParseError as exc:
        acuse = _build_acuse(
            exito=False,
            mensaje="Se ha producido un error en el proceso.",
            mensaje_interno=str(exc),
        )
        return Response(content=acuse, media_type="application/xml", status_code=422)
    except Exception as exc:  # noqa: BLE001
        acuse = _build_acuse(
            exito=False,
            mensaje="Se ha producido un error en el proceso.",
            mensaje_interno=str(exc),
        )
        return Response(content=acuse, media_type="application/xml", status_code=500)

    # 2. Registrar en el sistema
    try:
        inbound_id = await registrar_solicitud_dg(db, solicitud, opciones=opciones)
    except Exception as exc:  # noqa: BLE001
        detail = getattr(exc, "detail", str(exc))
        acuse = _build_acuse(
            exito=False,
            mensaje="Se ha producido un error en el proceso.",
            mensaje_interno=str(detail),
        )
        http_status = getattr(exc, "status_code", 500)
        return Response(content=acuse, media_type="application/xml", status_code=http_status)

    ord_consec = (solicitud.datos_generales.ord_consec if solicitud.datos_generales else "N/A")
    acuse = _build_acuse(
        exito=True,
        mensaje=(
            f"Solicitud recibida correctamente. "
            f"Orden HIS: {ord_consec}. "
            f"Solicitud interna: {inbound_id}. "
            f"Examenes: {len(solicitud.examenes)}."
        ),
    )
    return Response(content=acuse, media_type="application/xml", status_code=200)
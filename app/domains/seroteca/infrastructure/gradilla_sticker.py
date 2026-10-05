"""
Gradilla sticker generator — ZPL + PDF via Labelary API.

Label size: 4x2 inch at 8 dpmm.
"""

import base64
import io
import time
from datetime import datetime

import requests
from pypdf import PdfReader, PdfWriter

# Labelary API
LABELARY_URL = "http://api.labelary.com/v1/printers/8dpmm/labels/4x2/0/"
LABELARY_TIMEOUT = 15

def _format_date(dt) -> str:
    """Format a datetime as DD/MM/YYYY"""
    if dt is None:
        return "N/A"
    if isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y")
    return str(dt)


def build_zpl(rack, template: str) -> str:
    """Build a ZPL string from a Gradilla model instance and a ZPL template
    (leída de la tabla barcodes, label_type='GRADILLA' — ver BarcodeRepository)."""
    consecutivo = rack.g_number or "N/A"

    dias_descarte = "N/A"
    if rack.g_discard_date and rack.g_created_at:
        dias_descarte = str((rack.g_discard_date - rack.g_created_at).days)
        dias_int=int(dias_descarte)+1
    return template.format(
        consecutivo=consecutivo,
        dias_descarte=str(dias_int),
    )


def zpl_to_pdf(zpl: str) -> bytes:
    """Convert a ZPL string to PDF bytes via the Labelary API."""
    for attempt in range(3):
        response = requests.post(
            LABELARY_URL,
            headers={"Accept": "application/pdf"},
            files={"file": zpl},
            timeout=LABELARY_TIMEOUT,
        )
        if response.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.content
    response.raise_for_status()
    return response.content


def pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")


def generate_sticker(rack, template: str) -> dict:
    """
    Generate a sticker (ZPL + PDF base64) for a gradilla.

    Args:
        rack: Gradilla ORM model instance
        template: plantilla ZPL activa (label_type='GRADILLA')

    Returns:
        dict with keys: zpl_code, base64_pdf, gradilla_number, gradilla_id
    """
    zpl = build_zpl(rack, template)
    pdf_bytes = zpl_to_pdf(zpl)
    pdf_b64 = pdf_to_base64(pdf_bytes)

    return {
        "g_id": rack.g_id,
        "g_number": rack.g_number,
        "g_name": rack.g_name,
        "g_discard_date": _format_date(rack.g_discard_date),
        "zpl_code": zpl,
        "base64_pdf": pdf_b64,
    }
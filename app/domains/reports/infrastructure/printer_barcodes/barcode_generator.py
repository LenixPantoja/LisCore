"""
ZPL generator for barcode tube stickers.
PDF preview via Labelary API (http://api.labelary.com).

Label size: 2 x 1 inch at 8 dpmm (≈ 50 mm × 25 mm).
"""
import base64
import io
import time
from typing import List, Sequence, Tuple

import requests
from pypdf import PdfReader, PdfWriter

# ── Labelary API ────────────────────────────────────────────────────────────
LABELARY_URL = "http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/"
LABELARY_TIMEOUT = 15  # seconds

def build_zpl(sticker: dict, template: str) -> str:
    """Build a ZPL string from a sticker data dict and a ZPL template (leída
    de la tabla barcodes, label_type='MUESTRA' — ver BarcodeRepository)."""
    return template.format(
        patient_full_name=sticker["patient_full_name"],
        document_type=sticker.get("document_type", ""),
        identification=sticker["identification"],
        enterprise_name=sticker["enterprise_name"],
        age_str=sticker["age_str"],
        barcode_value=sticker["barcode_value"],
        label_number=sticker["label_number"],
        work_group_name=sticker["work_group_name"],
        tests_line=sticker["tests_line"],
        sample_type_name=sticker.get("sample_type_name", ""),
        piso=sticker.get("piso", ""),
        consecutivo=sticker.get("hq_consecutive", ""),
    )


class _BlankOnMissing(dict):
    """Variables de plantilla no conocidas se reemplazan por vacío en vez de fallar."""
    def __missing__(self, key):
        return ""


def build_order_label_zpl(data: dict, template: str) -> str:
    """ZPL de la etiqueta de la orden (barcodes.label_type='ORDEN')."""
    return template.format_map(_BlankOnMissing(
        nombre_sede=data.get("nombre_sede", ""),
        numero_orden=data.get("numero_orden", ""),
        fecha_creacion_orden=data.get("fecha_creacion_orden", ""),
        consecutivo_sede=data.get("consecutivo_sede", ""),
        nombres_paciente=data.get("nombres_paciente", ""),
        tipodoc=data.get("tipodoc", ""),
        # La plantilla usa "numero_documeto"; se acepta también bien escrito
        numero_documeto=data.get("numero_documento", ""),
        numero_documento=data.get("numero_documento", ""),
    ))


def zpl_to_pdf(zpl: str) -> bytes:
    """Convert a ZPL string to PDF bytes via the Labelary API.

    Retries up to 3 times with exponential backoff on 429 rate-limit responses.
    """
    for attempt in range(3):
        response = requests.post(
            LABELARY_URL,
            headers={"Accept": "application/pdf"},
            files={"file": zpl.encode("utf-8")},
            timeout=LABELARY_TIMEOUT,
        )
        if response.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.content
    response.raise_for_status()
    return response.content  # unreachable but satisfies type checker


def _merge_pdfs(pdf_bytes_list: List[bytes]) -> bytes:
    """Merge a list of single-page PDFs into one multi-page PDF."""
    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def build_labels_result(labels: Sequence[Tuple[str, int]]) -> tuple[bytes, List[str]]:
    """Generate a merged PDF and the ZPL codes for a list of (zpl, copies).

    Each label is repeated `copies` times (barcodes.number_labels_print) both
    in the ZPL list and in the PDF, keeping the given order. Labelary is
    called only once per label, not once per copy.

    Returns:
        (merged_pdf_bytes, zpl_codes)
    """
    zpl_list: List[str] = []
    pdf_list: List[bytes] = []
    for i, (zpl, copies) in enumerate(labels):
        pdf = zpl_to_pdf(zpl)
        copies = max(int(copies or 1), 1)
        zpl_list.extend([zpl] * copies)
        pdf_list.extend([pdf] * copies)
        if i < len(labels) - 1:
            time.sleep(0.5)  # avoid 429 rate-limit between requests
    return _merge_pdfs(pdf_list), zpl_list


def build_stickers_result(
    stickers: List[dict], template: str, copies: int = 1
) -> tuple[bytes, List[str]]:
    """Generate a merged PDF and ZPL codes for all sample stickers."""
    return build_labels_result([(build_zpl(s, template), copies) for s in stickers])


def pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")

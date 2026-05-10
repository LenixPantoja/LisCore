"""
ZPL generator for barcode tube stickers.
PDF preview via Labelary API (http://api.labelary.com).

Label size: 2 x 1 inch at 8 dpmm (≈ 50 mm × 25 mm).
"""
import base64
import io
import time
from typing import List

import requests
from pypdf import PdfReader, PdfWriter

# ── Labelary API ────────────────────────────────────────────────────────────
LABELARY_URL = "http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/"
LABELARY_TIMEOUT = 15  # seconds

# ── ZPL template ────────────────────────────────────────────────────────────
_ZPL_TEMPLATE = """\
^XA
^LH0,0
^FO45,20^AB,20,1^FD{patient_full_name}^FS
^FO45,45^AB,10,1^FDIDENTIFICACION:{identification}^FS
^FO45,60^AB,10,1^FDEMPRESA:{enterprise_name}^FS
^FO260,60^AB,10,1^FDEDAD:{age_str}^FS

^BY2,3,150
^FO28,80^BCN,80,N,Y,N^FD{barcode_value}^FS

^FO370,40^ADB,25,1^FD{label_number}^FS
^FO5,80^ABB,15,1^FD{work_group_name}^FS

^FO45,165^AB,18,1^FD{tests_line}^FS
^FO45,189^AB,10,1^FD TM-{sample_type_name}^FS

^PQ1
^XZ"""


def build_zpl(sticker: dict) -> str:
    """Build a ZPL string from a sticker data dict."""
    return _ZPL_TEMPLATE.format(
        patient_full_name=sticker["patient_full_name"],
        identification=sticker["identification"],
        enterprise_name=sticker["enterprise_name"],
        age_str=sticker["age_str"],
        barcode_value=sticker["barcode_value"],
        label_number=sticker["label_number"],
        work_group_name=sticker["work_group_name"],
        tests_line=sticker["tests_line"],
        sample_type_name=sticker.get("sample_type_name", ""),
    )


def zpl_to_pdf(zpl: str) -> bytes:
    """Convert a ZPL string to PDF bytes via the Labelary API.

    Retries up to 3 times with exponential backoff on 429 rate-limit responses.
    """
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


def build_stickers_result(stickers: List[dict]) -> tuple[bytes, List[str]]:
    """Generate a merged PDF and ZPL codes for all stickers.

    Calls the Labelary API once per sticker, merges the resulting PDFs,
    and returns the merged PDF alongside the raw ZPL strings.

    Returns:
        (merged_pdf_bytes, zpl_codes)
    """
    zpl_list = [build_zpl(s) for s in stickers]
    pdf_list: List[bytes] = []
    for i, zpl in enumerate(zpl_list):
        pdf_list.append(zpl_to_pdf(zpl))
        if i < len(zpl_list) - 1:
            time.sleep(0.5)  # avoid 429 rate-limit between requests
    merged_pdf = _merge_pdfs(pdf_list)
    return merged_pdf, zpl_list


def pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")

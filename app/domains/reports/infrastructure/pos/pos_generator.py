import base64
import io
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ─── Company constants (LISCORE) ─────────────────────────────────────────────
COMPANY_NAME = "LISCORE"
COMPANY_NIT = "NIT: 1007736480-1"
COMPANY_ADDRESS = "CRA 32B # 19-02 PASTO(NARIÑO)"  
COMPANY_PHONE = "Tel: 3158357923 - 3184510394"
COMPANY_EMAIL = "liscore@panthosoft.com"

# ─── Layout ───────────────────────────────────────────────────────────────────
TICKET_WIDTH = 75 * mm
TICKET_MARGIN = 3 * mm
CONTENT_WIDTH = TICKET_WIDTH - 2 * TICKET_MARGIN

# ─── Priority mapping ─────────────────────────────────────────────────────────
PRIORITY_LABELS = {0: "Normal", 1: "Urgente", 2: "Muy Urgente"}

# ─── Colors ───────────────────────────────────────────────────────────────────
C_BLACK = colors.black
C_DARK = colors.black
C_GRAY = colors.black
C_LIGHT_GRAY = colors.white
C_WHITE = colors.white


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _age_from_dob(dob: Optional[date]) -> str:
    if not dob:
        return "-"
    today = date.today()
    years = (
        today.year - dob.year
        - ((today.month, today.day) < (dob.month, dob.day))
    )
    return f"{years} años"


def _fmt_currency(value) -> str:
    if value is None:
        return "$0"
    try:
        int_val = int(Decimal(str(value)))
        return f"${int_val:,}".replace(",", ".")
    except Exception:
        return "$0"


def _safe(value, fallback: str = "-") -> str:
    if value is None or str(value).strip() == "":
        return fallback
    return str(value)


# ─── Styles ───────────────────────────────────────────────────────────────────

def _styles() -> dict:
    return {
        "company_name": ParagraphStyle(
            "company_name",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            alignment=TA_CENTER,
            textColor=C_BLACK,
        ),
        "company_sub": ParagraphStyle(
            "company_sub",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=C_BLACK,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=C_BLACK,
        ),
        "data_label": ParagraphStyle(
            "data_label",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=C_BLACK,
        ),
        "data_value": ParagraphStyle(
            "data_value",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=C_BLACK,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=C_BLACK,
        ),
        "table_header_right": ParagraphStyle(
            "table_header_right",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=C_BLACK,
            alignment=TA_RIGHT,
        ),
        "table_center": ParagraphStyle(
            "table_center",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
        ),
        "table_right": ParagraphStyle(
            "table_right",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=TA_RIGHT,
        ),
        "total_label": ParagraphStyle(
            "total_label",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=C_BLACK,
        ),
        "total_value": ParagraphStyle(
            "total_value",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=C_BLACK,
            alignment=TA_RIGHT,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            alignment=TA_CENTER,
            textColor=C_BLACK,
        ),
    }


# ─── HR Helpers ───────────────────────────────────────────────────────────────

def _hr(dashed: bool = False) -> HRFlowable:
    dash = (2, 2) if dashed else None
    return HRFlowable(
        width="100%",
        thickness=1.0,
        color=C_BLACK,
        spaceAfter=2,
        spaceBefore=2,
        dash=dash,
    )


# ─── Main builder ─────────────────────────────────────────────────────────────

def build_pos_ticket(
    order,
    patient,
    enterprise,
    diagnosis,
    app_user,
    studies: List[Tuple],  # [(study_name: str, tariff_value: Decimal|None)]
) -> bytes:
    """
    Build an 80mm POS PDF ticket and return as bytes.

    Parameters
    ----------
    order       : Order ORM object
    patient     : Patient ORM object (or None)
    enterprise  : Enterprise ORM object (order's enterprise, or None)
    diagnosis   : Diagnosis ORM object (or None)
    app_user    : AppUser ORM object (or None)
    studies     : list of (study_name, tariff_value) tuples
    """
    buf = io.BytesIO()

    # Tall page — content determines rendered height
    doc = SimpleDocTemplate(
        buf,
        pagesize=(TICKET_WIDTH, 900 * mm),
        rightMargin=TICKET_MARGIN,
        leftMargin=TICKET_MARGIN,
        topMargin=TICKET_MARGIN,
        bottomMargin=TICKET_MARGIN,
    )

    s = _styles()
    story = []

    col_label = CONTENT_WIDTH * 0.42
    col_value = CONTENT_WIDTH * 0.58

    # ── HEADER 1: Company data ─────────────────────────────────────────────
    story.append(Paragraph(COMPANY_NAME, s["company_name"]))
    story.append(Spacer(1, 1))
    story.append(Paragraph(COMPANY_NIT, s["company_sub"]))
    story.append(Paragraph(COMPANY_ADDRESS, s["company_sub"]))
    story.append(Paragraph(COMPANY_PHONE, s["company_sub"]))
    story.append(Paragraph(COMPANY_EMAIL, s["company_sub"]))
    story.append(Spacer(1, 3))
    story.append(_hr())

    # ── HEADER 2: Patient data ─────────────────────────────────────────────
    story.append(Paragraph("INFORMACIÓN DEL PACIENTE", s["section_header"]))
    story.append(_hr())

    # Build patient field values
    patient_name = " ".join(
        filter(
            None,
            [
                getattr(patient, "pt_firts_name", None),
                getattr(patient, "pt_middle_name", None),
                getattr(patient, "pt_last_name", None),
                getattr(patient, "pt_second_last_name", None),
            ],
        )
    ) if patient else "-"

    doc_type_code = (
        patient.document_type.dt_code
        if patient and getattr(patient, "document_type", None)
        else "-"
    )
    sex_name = (
        patient.sex_type.name
        if patient and getattr(patient, "sex_type", None)
        else "-"
    )
    age = _age_from_dob(getattr(patient, "pt_date_of_birth", None) if patient else None)
    enterprise_name = _safe(getattr(enterprise, "en_name", None))
    diag_code = _safe(getattr(diagnosis, "diag_code", None))
    priority_label = PRIORITY_LABELS.get(order.o_priority or 0, "Normal")
    user_name = " ".join(
        filter(
            None,
            [
                getattr(app_user, "usr_first_name", None),
                getattr(app_user, "usr_last_name", None),
            ],
        )
    ) if app_user else "-"

    patient_fields = [
        ("PACIENTE", patient_name),
        ("DOCUMENTO", _safe(getattr(patient, "pt_Number_document", None))),
        ("TIPO DOCUMENTO", doc_type_code),
        ("EDAD", age),
        ("SEXO", sex_name),
        ("CELULAR", _safe(getattr(patient, "pt_phone_number", None))),
        ("EMPRESA INGRESO", enterprise_name),
        ("DX CIE10", diag_code),
        ("PRIORIDAD", priority_label),
        ("CORREO", _safe(getattr(patient, "pt_mail", None))),
        ("DIRECCIÓN", _safe(getattr(patient, "pt_address", None))),
        ("N° ORDEN", _safe(order.o_number)),
        ("F. INGRESO", str(order.o_date) if order.o_date else "-"),
        ("F. IMPRESIÓN", str(date.today())),
        ("ATENDIDO POR", user_name),
    ]

    for label, value in patient_fields:
        row = [[Paragraph(label, s["data_label"]), Paragraph(value, s["data_value"])]]
        t = Table(row, colWidths=[col_label, col_value])
        t.setStyle(
            TableStyle(
                [
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(t)

    story.append(Spacer(1, 3))
    story.append(_hr())

    # ── BODY: Exam table ───────────────────────────────────────────────────
    story.append(Paragraph("EXÁMENES SOLICITADOS", s["section_header"]))
    story.append(_hr())

    col_item = CONTENT_WIDTH * 0.08
    col_exam = CONTENT_WIDTH * 0.62
    col_val = CONTENT_WIDTH * 0.30

    header_row = [
        Paragraph("#", s["table_header"]),
        Paragraph("EXAMEN", s["table_header"]),
        Paragraph("VALOR", s["table_header_right"]),
    ]

    table_data = [header_row]
    total = Decimal("0")

    for i, (study_name, tariff_value) in enumerate(studies, start=1):
        val = Decimal(str(tariff_value)) if tariff_value is not None else Decimal("0")
        total += val
        table_data.append(
            [
                Paragraph(str(i), s["table_center"]),
                Paragraph(_safe(study_name), s["table_cell"]),
                Paragraph(_fmt_currency(val), s["table_right"]),
            ]
        )

    exam_table = Table(table_data, colWidths=[col_item, col_exam, col_val])
    exam_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), C_WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_WHITE]),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, C_BLACK),
            ]
        )
    )
    story.append(exam_table)

    # Total row
    story.append(Spacer(1, 2))
    story.append(_hr(dashed=True))

    total_row = [
        [
            Paragraph("TOTAL:", s["total_label"]),
            Paragraph(_fmt_currency(total), s["total_value"]),
        ]
    ]
    total_table = Table(total_row, colWidths=[CONTENT_WIDTH * 0.5, CONTENT_WIDTH * 0.5])
    total_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(total_table)
    story.append(Spacer(1, 5))
    story.append(_hr())

    # ── FOOTER ────────────────────────────────────────────────────────────
    story.append(
        Paragraph(
            "Este documento no constituye una factura electrónica. "
            "Su factura oficial será enviada al correo electrónico "
            "proporcionado durante el registro.",
            s["footer"],
        )
    )
    story.append(Spacer(1, 4))

    doc.build(story)
    return buf.getvalue()


def pos_pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")

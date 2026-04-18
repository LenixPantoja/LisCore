import io
import base64
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.pdfgen import canvas as pdf_canvas


# ─────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 1.5 * cm

LAB_STATE_LABELS = {
    0: "Pendiente",
    1: "Registrado",
    2: "Validado",
}

ORDER_STATE_LABELS = {
    1: "Activa",
    2: "Cerrada",
    3: "Anulada",
}

SEX_LABELS = {
    1: "Femenino",
    2: "Masculino",
}


# ─────────────────────────────────────────────
# Canvas con marca de agua y pie de página
# ─────────────────────────────────────────────
class _WatermarkCanvas(pdf_canvas.Canvas):
    """Canvas personalizado que dibuja marca de agua y pie de página en cada página."""

    def __init__(self, *args, generation_date: str, **kwargs):
        super().__init__(*args, **kwargs)
        self._generation_date = generation_date
        self._saved_page_states: list = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_watermark()
            self._draw_footer(total_pages)
            pdf_canvas.Canvas.showPage(self)
        pdf_canvas.Canvas.save(self)

    def _draw_watermark(self):
        self.saveState()
        self.translate(PAGE_WIDTH / 2, PAGE_HEIGHT / 2)
        self.rotate(45)
        self.setFont("Helvetica-Bold", 90)
        self.setFillColorRGB(0.88, 0.88, 0.88)
        self.drawCentredString(0, 0, "LisCore")
        self.restoreState()

    def _draw_footer(self, total_pages: int):
        page_number = self._saved_page_states.index(
            {k: v for k, v in self.__dict__.items() if k in self._saved_page_states[0]}
        ) + 1 if hasattr(self, "_pageNumber") else self._pageNumber

        self.saveState()
        self.setFont("Helvetica", 7)
        self.setFillColorRGB(0.45, 0.45, 0.45)
        footer_y = 0.7 * cm
        left_text = f"Generado por: LisCore  |  Sistema LIS  |  {self._generation_date}"
        right_text = f"Página {self._pageNumber} de {total_pages}"
        self.drawString(MARGIN, footer_y, left_text)
        self.drawRightString(PAGE_WIDTH - MARGIN, footer_y, right_text)
        # Línea separadora
        self.setStrokeColorRGB(0.8, 0.8, 0.8)
        self.line(MARGIN, footer_y + 0.4 * cm, PAGE_WIDTH - MARGIN, footer_y + 0.4 * cm)
        self.restoreState()


# ─────────────────────────────────────────────
# Función pública principal
# ─────────────────────────────────────────────
def build_laboratory_pdf(order: Any, patient: Any, laboratories: list) -> bytes:
    """
    Construye el PDF de resultados de laboratorio y retorna los bytes.

    :param order: instancia ORM de Order (con patient y enterprise cargados).
    :param patient: instancia ORM de Patient.
    :param laboratories: lista de instancias ORM de Laboratory
                         (con order_detail.study y test cargados).
    :return: bytes del PDF generado.
    """
    buffer = io.BytesIO()
    generation_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=2 * cm,
        canvasmaker=lambda *args, **kwargs: _WatermarkCanvas(
            *args, generation_date=generation_date, **kwargs
        ),
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Encabezado ────────────────────────────────────────────
    story += _build_header(order, patient, styles, generation_date)
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2563EB")))
    story.append(Spacer(1, 0.4 * cm))

    # ── Cuerpo: resultados agrupados por estudio ───────────────
    story += _build_body(laboratories, patient, styles)

    doc.build(story)
    return buffer.getvalue()


# ─────────────────────────────────────────────
# Sección: cabecera
# ─────────────────────────────────────────────
def _build_header(order: Any, patient: Any, styles: Any, generation_date: str) -> list:
    elements = []

    title_style = ParagraphStyle(
        "title",
        parent=styles["Normal"],
        fontSize=18,
        textColor=colors.HexColor("#2563EB"),
        fontName="Helvetica-Bold",
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "subtitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=0,
    )
    label_style = ParagraphStyle(
        "label",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#64748B"),
        fontName="Helvetica-Bold",
        spaceAfter=0,
    )
    value_style = ParagraphStyle(
        "value",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=2,
    )

    # — Fila superior: nombre sistema | empresa
    enterprise_name = order.enterprise.en_name if order.enterprise else "—"
    header_data = [
        [
            Paragraph("LisCore", title_style),
            Paragraph(f"<b>{enterprise_name}</b>", value_style),
        ]
    ]
    header_table = Table(header_data, colWidths=[(PAGE_WIDTH - 2 * MARGIN) * 0.4, (PAGE_WIDTH - 2 * MARGIN) * 0.6])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    elements.append(header_table)
    elements.append(Paragraph("Sistema de Información de Laboratorio Clínico", subtitle_style))
    elements.append(Spacer(1, 0.5 * cm))

    # — Datos demográficos del paciente
    full_name = _patient_full_name(patient)
    doc_number = patient.pt_Number_document if patient else "—"
    dob = patient.pt_date_of_birth.strftime("%d/%m/%Y") if patient and patient.pt_date_of_birth else "—"
    sex = SEX_LABELS.get(patient.pt_sex_type, "—") if patient else "—"
    age = order.o_age if order.o_age else "—"

    # — Datos de la orden
    order_number = order.o_number
    order_date = order.o_date.strftime("%d/%m/%Y") if order.o_date else "—"
    order_state = ORDER_STATE_LABELS.get(order.o_order_state, str(order.o_order_state))

    col_w = (PAGE_WIDTH - 2 * MARGIN) / 4

    demo_data = [
        [
            Paragraph("DATOS DEL PACIENTE", label_style),
            Paragraph("", label_style),
            Paragraph("DATOS DE LA ORDEN", label_style),
            Paragraph("", label_style),
        ],
        [
            Paragraph("Nombre:", label_style),
            Paragraph(full_name, value_style),
            Paragraph("N° Orden:", label_style),
            Paragraph(order_number, value_style),
        ],
        [
            Paragraph("Documento:", label_style),
            Paragraph(doc_number, value_style),
            Paragraph("Fecha:", label_style),
            Paragraph(order_date, value_style),
        ],
        [
            Paragraph("Fecha Nacimiento:", label_style),
            Paragraph(dob, value_style),
            Paragraph("Estado:", label_style),
            Paragraph(order_state, value_style),
        ],
        [
            Paragraph("Edad:", label_style),
            Paragraph(age, value_style),
            Paragraph("Impreso:", label_style),
            Paragraph(generation_date, value_style),
        ],
        [
            Paragraph("Sexo:", label_style),
            Paragraph(sex, value_style),
            Paragraph("", label_style),
            Paragraph("", value_style),
        ],
    ]

    demo_table = Table(demo_data, colWidths=[col_w * 0.8, col_w * 1.2, col_w * 0.8, col_w * 1.2])
    demo_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (2, 0), (3, 0)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#BFDBFE")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
    ]))
    elements.append(demo_table)

    return elements


# ─────────────────────────────────────────────
# Sección: cuerpo de resultados
# ─────────────────────────────────────────────
def _build_body(laboratories: list, patient: Any, styles: Any) -> list:
    elements = []

    study_style = ParagraphStyle(
        "study_header",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1E40AF"),
        spaceBefore=8,
        spaceAfter=4,
    )
    col_header_style = ParagraphStyle(
        "col_header",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    cell_style = ParagraphStyle(
        "cell",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#1E293B"),
    )
    note_style = ParagraphStyle(
        "note",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.HexColor("#64748B"),
        leftIndent=4,
    )

    # Agrupar laboratorios por estudio
    grouped: dict[str, list] = {}
    for lab in laboratories:
        study_name = "Sin estudio asignado"
        if lab.order_detail and lab.order_detail.study:
            study_name = lab.order_detail.study.name
        grouped.setdefault(study_name, []).append(lab)

    is_female = patient and patient.pt_sex_type == 1

    col_widths = _result_col_widths()

    for study_name, labs in grouped.items():
        elements.append(Paragraph(study_name, study_style))

        # Cabecera de tabla
        table_data = [[
            Paragraph("Examen", col_header_style),
            Paragraph("Resultado", col_header_style),
            Paragraph("Unidades", col_header_style),
            Paragraph("Valor de Referencia", col_header_style),
            Paragraph("Estado", col_header_style),
        ]]

        for lab in labs:
            test = lab.test
            test_name = test.name if test else "—"
            units = test.units if test and test.units else "—"

            result = _format_result(lab)
            reference = _format_reference(test, is_female) if test else "—"
            state_label = LAB_STATE_LABELS.get(lab.l_state, str(lab.l_state) if lab.l_state is not None else "—")

            row = [
                Paragraph(test_name, cell_style),
                Paragraph(result, cell_style),
                Paragraph(units, cell_style),
                Paragraph(reference, cell_style),
                Paragraph(state_label, cell_style),
            ]
            table_data.append(row)

            # Nota de validación como fila fusionada si existe
            if lab.l_nota_validation:
                note_row = [
                    Paragraph(f"Nota: {lab.l_nota_validation}", note_style),
                    "", "", "", "",
                ]
                table_data.append(note_row)

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(_result_table_style(table_data))
        elements.append(t)
        elements.append(Spacer(1, 0.3 * cm))

    if not grouped:
        elements.append(Paragraph("No hay resultados registrados para esta orden.", styles["Normal"]))

    return elements


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _patient_full_name(patient: Any) -> str:
    if not patient:
        return "—"
    parts = [
        patient.pt_firts_name,
        patient.pt_middle_name or "",
        patient.pt_last_name,
        patient.pt_second_last_name or "",
    ]
    return " ".join(p for p in parts if p).strip()


def _format_result(lab: Any) -> str:
    if lab.l_result_num is not None:
        return str(lab.l_result_num)
    if lab.l_result:
        return lab.l_result
    return "—"


def _format_reference(test: Any, is_female: bool) -> str:
    if is_female:
        lo, hi = test.female_value_min, test.female_value_max
    else:
        lo, hi = test.male_value_min, test.male_value_max

    if lo is not None and hi is not None:
        return f"{lo} – {hi}"
    if lo is not None:
        return f">= {lo}"
    if hi is not None:
        return f"<= {hi}"
    return "—"


def _result_col_widths() -> list:
    usable = PAGE_WIDTH - 2 * MARGIN
    return [usable * 0.30, usable * 0.15, usable * 0.13, usable * 0.27, usable * 0.15]


def _result_table_style(data: list) -> TableStyle:
    style = [
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        # Filas alternas
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        # Bordes
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        # Alineación
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]

    # Fusionar celdas de las filas de notas (span de columna 0 al final)
    for i, row in enumerate(data[1:], start=1):
        if isinstance(row[1], str) and row[1] == "":
            style.append(("SPAN", (0, i), (4, i)))
            style.append(("BACKGROUND", (0, i), (4, i), colors.HexColor("#FFFBEB")))

    return TableStyle(style)


# ─────────────────────────────────────────────
# Encoder a Base64
# ─────────────────────────────────────────────
def pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")

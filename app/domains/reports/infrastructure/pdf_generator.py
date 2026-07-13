import base64
import io
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable,
    Image as RLImage,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.utils import ImageReader

# ─────────────────────────────────────────────
# Constantes de mapeo
# ─────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).parent / "templates"
WATERMARK_PNG = str(TEMPLATES_DIR / "LogoRojoPabon.png")
LOGO_PNG = str(TEMPLATES_DIR / "LogoRojoPabon.png")  # Usamos la misma imagen como logo
LOGO_BLUE_PNG = str(TEMPLATES_DIR / "LogoAzulPabon.png")


class _RoundedFrame(Flowable):
    """Envuelve un flowable con un borde de esquinas redondeadas."""

    def __init__(self, content: Flowable, radius: float = 5, color=None):
        Flowable.__init__(self)
        self._content = content
        self._radius = radius
        self._color = color or colors.HexColor("#bfdbfe")
        self._w = self._h = 0

    def wrap(self, available_w, available_h):
        self._w, self._h = self._content.wrap(available_w, available_h)
        return self._w, self._h

    def split(self, available_w, available_h):
        parts = self._content.split(available_w, available_h)
        return [_RoundedFrame(p, self._radius, self._color) for p in parts]

    def draw(self):
        c = self.canv
        c.saveState()
        c.setStrokeColor(self._color)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, self._w, self._h, self._radius, stroke=1, fill=0)
        c.restoreState()
        self._content.drawOn(c, 0, 0)


def _load_watermark_image(opacity: float = 0.10) -> io.BytesIO:
    """Carga el PNG de la marca de agua y le aplica la opacidad indicada."""
    img = PILImage.open(WATERMARK_PNG).convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda x: int(x * opacity))
    img = PILImage.merge("RGBA", (r, g, b, a))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


_WATERMARK_BUF: io.BytesIO | None = None


def _get_watermark() -> io.BytesIO:
    global _WATERMARK_BUF
    if _WATERMARK_BUF is None:
        _WATERMARK_BUF = _load_watermark_image(0.10)
    _WATERMARK_BUF.seek(0)
    return _WATERMARK_BUF


def _get_logo() -> ImageReader:
    """Carga el logo para la cabecera."""
    return ImageReader(LOGO_PNG)


def _get_logo_blue() -> ImageReader:
    """Carga el logo azul para la cabecera."""
    return ImageReader(LOGO_BLUE_PNG)


def _fetch_signature_image(object_name: str | None) -> io.BytesIO | None:
    """Descarga la firma desde el bucket 'signatures' de MinIO y la retorna como BytesIO."""
    if not object_name:
        return None
    try:
        from utils.minio_client import get_minio_client
        from app.core.config import settings as _settings
        client = get_minio_client()
        response = client.get_object(_settings.MINIO_SIGNATURES_BUCKET, object_name)
        buf = io.BytesIO(response.read())
        response.close()
        response.release_conn()
        buf.seek(0)
        return buf
    except Exception:
        return None


def _fetch_graphic_image(object_name: str | None) -> io.BytesIO | None:
    """Descarga una imagen del bucket 'graphics' de MinIO y la retorna como BytesIO.

    Retorna None si object_name está vacío o si ocurre cualquier error.
    """
    if not object_name:
        return None
    try:
        from utils.minio_client import get_minio_client
        from app.core.config import settings as _settings
        client = get_minio_client()
        response = client.get_object(_settings.MINIO_GRAPHICS_BUCKET, object_name)
        buf = io.BytesIO(response.read())
        response.close()
        response.release_conn()
        buf.seek(0)
        return buf
    except Exception:
        return None


# Colores corporativos
C_NAVY   = colors.HexColor("#233248")
C_WHITE  = colors.white
C_DARK   = colors.HexColor("#1d293c")
C_GRAY   = colors.HexColor("#4a5568")
C_LIGHT  = colors.HexColor("#f0f6ff")
C_RED    = colors.HexColor("#993c1d")
C_GREEN  = colors.HexColor("#0f6e56")
C_BLUE2  = colors.HexColor("#233248")

LAB_STATE_LABELS = {
    0: ("Sin Resultados", "pendiente"),
    1: ("Pendiente", "pendiente"),
    2: ("Con Resultados", "registrado"),
    3: ("Validada", "validado"),
    4: ("Impreso", "validado"),
}

SEX_LABELS = {
    1: "Femenino",
    2: "Masculino",
}


# ─────────────────────────────────────────────
# Función pública principal
# ─────────────────────────────────────────────
def build_laboratory_pdf(
    order: Any,
    patient: Any,
    laboratories: list,
    signatures_map: dict | None = None,
) -> bytes:
    """
    Genera el PDF del reporte de laboratorio usando reportlab.
    La cabecera (logo + datos del paciente) se repite en todas las páginas.
    """
    generation_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    is_female = patient and patient.pt_sex_type == 1
    print_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── Datos de contexto ──────────────────────────────
    patient_name  = _full_name(patient)
    patient_doc   = patient.pt_Number_document if patient else "—"
    sex           = SEX_LABELS.get(patient.pt_sex_type, "—") if patient else "—"
    age           = str(order.o_age or "—")
    enterprise    = order.enterprise.en_name if order.enterprise else "—"
    service_name  = order.service.name if order.service else "—"
    order_date    = order.o_date.strftime("%d/%m/%Y") if order.o_date else "—"
    order_number  = str(order.o_number or "—")

    # Ciudad
    city_name = "—"
    if patient and hasattr(patient, "city") and patient.city:
        city_name = getattr(patient.city, "city_name", None) or "—"

    studies = _group_by_study(laboratories, is_female)

    # ── Estilos de texto ───────────────────────────────
    s_label    = ParagraphStyle("label",    fontName="Helvetica-Bold", fontSize=7, textColor=C_NAVY)
    s_value    = ParagraphStyle("value",    fontName="Helvetica",      fontSize=8,  textColor=C_DARK)
    s_study    = ParagraphStyle("study",    fontName="Helvetica-Bold", fontSize=8,  textColor=C_NAVY)
    s_wg       = ParagraphStyle("wg",       fontName="Helvetica-Bold", fontSize=9,  textColor=C_NAVY)
    s_th       = ParagraphStyle("th",       fontName="Helvetica-Bold", fontSize=7,  textColor=C_NAVY)
    s_test     = ParagraphStyle("test",     fontName="Helvetica-Bold", fontSize=8,  textColor=C_DARK)
    s_res_ok   = ParagraphStyle("res_ok",   fontName="Helvetica-Bold", fontSize=8,  textColor=C_GREEN)
    s_res_bad  = ParagraphStyle("res_bad",  fontName="Helvetica-Bold", fontSize=8,  textColor=C_RED)
    s_unit     = ParagraphStyle("unit",     fontName="Helvetica",      fontSize=8,  textColor=C_BLUE2)
    s_ref      = ParagraphStyle("ref",      fontName="Helvetica",      fontSize=8,  textColor=C_GRAY)
    s_empty    = ParagraphStyle("empty",    fontName="Helvetica-Oblique", fontSize=8, textColor=C_NAVY)
    s_ent      = ParagraphStyle("ent",      fontName="Helvetica-Bold", fontSize=10, textColor=C_NAVY,  alignment=TA_RIGHT)
    s_ent_s    = ParagraphStyle("ent_s",    fontName="Helvetica",      fontSize=7,  textColor=C_GRAY,  alignment=TA_RIGHT)
    s_comp     = ParagraphStyle("comp",     fontName="Courier",         fontSize=7.5, textColor=C_DARK, leading=11, leftIndent=8)
    s_alt_ref  = ParagraphStyle("alt_ref",  fontName="Helvetica-Oblique", fontSize=7,   textColor=C_GRAY, leading=10, leftIndent=8)

    # ── Página: letter, márgenes ───────────────────────
    PAGE_W, PAGE_H = letter
    LEFT = RIGHT = 1.5 * cm
    TOP  = 6 * cm  # Aumentado para dejar espacio a la cabecera que dibujaremos manualmente
    BOT  = 3.0 * cm
    COL_W = PAGE_W - LEFT - RIGHT

    # Guardamos los datos del paciente en variables globales para usarlos en el canvas
    header_data = {
        'logo': _get_logo(),
        'logo_blue': _get_logo_blue(),
        's_ent': s_ent,
        's_ent_s': s_ent_s,
        's_label': s_label,
        's_value': s_value,
        'patient_name': patient_name,
        'patient_doc': patient_doc,
        'order_number': order_number,
        'enterprise': enterprise,
        'age': age,
        'city_name': city_name,
        'sex': sex,
        'service_name': service_name,
        'order_date': order_date,
        'print_date': print_date,
        'PAGE_W': PAGE_W,
        'PAGE_H': PAGE_H,
        'LEFT': LEFT,
        'RIGHT': RIGHT,
        'COL_W': COL_W,
        'C_NAVY': C_NAVY,
        'C_WHITE': C_WHITE,
        'C_GRAY': C_GRAY,
    }

    # ── Story principal (solo los resultados) ───────────
    story = []

    # ── Resultados por estudio ──────────────────────────
    if studies:
        for wg_group in studies:
            wg_hdr = Table(
                [[Paragraph(wg_group["wg_name"].upper(), s_wg)]],
                colWidths=[COL_W],
            )
            wg_hdr.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, -1), colors.transparent),
                ("TOPPADDING",  (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(wg_hdr)

            # ── Precompute signature groups ──
            # Consecutive studies sharing the exact same set of validators
            # will share a single signature block rendered after the last study.
            _wg_study_list = wg_group["studies"]
            def _sig_key(s):
                sigs = (signatures_map or {}).get(s["id"], [])
                return frozenset(s["user_name"] for s in sigs) if sigs else None
            _sig_keys = [_sig_key(s) for s in _wg_study_list]
            _last_of_group = [
                (i == len(_sig_keys) - 1) or (_sig_keys[i] != _sig_keys[i + 1])
                for i in range(len(_sig_keys))
            ]

            for idx, study in enumerate(wg_group["studies"]):
                study_hdr = Table(
                    [[Paragraph(study["name"].upper(), s_study)]],
                    colWidths=[COL_W],
                )
                study_hdr.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.transparent),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(study_hdr)

                th_row = [
                    Paragraph("EXAMEN", s_th),
                    Paragraph("RESULTADO", s_th),
                    Paragraph("UNIDADES", s_th),
                    Paragraph("VALOR DE REFERENCIA", s_th),
                ]
                res_rows = [th_row]
                # Compound results are collected separately so they can be rendered
                # as standalone flowables after the table. Embedding them as table
                # rows with SPAN prevents Table.split() from working when the
                # compound text is taller than a full page, causing LayoutError.
                pending_compounds: list[dict] = []

                for row in study["rows"]:
                    ref_text = row["reference"]
                    alt_ref = (row.get("alternative_range_value") or "").strip()
                    if alt_ref:
                        ref_text = f"{ref_text}<br/>{alt_ref}"
                    res_rows.append([
                        Paragraph(row["test_name"], s_test),
                        Paragraph(row["result"], s_res_bad if row["is_abnormal"] else s_res_ok),
                        Paragraph(row["units"], s_unit),
                        Paragraph(ref_text, s_ref),
                    ])
                    if row.get("result_comp"):
                        pending_compounds.append({
                            "result_comp": row["result_comp"],
                            "alternative_range_value": row.get("alternative_range_value"),
                        })

                col_widths = [COL_W * 0.35, COL_W * 0.18, COL_W * 0.14, COL_W * 0.33]
                res_tbl = Table(res_rows, colWidths=col_widths, repeatRows=1)

                tbl_style = [
                    ("BACKGROUND",  (0, 0), (-1, 0),  colors.transparent),
                    ("TOPPADDING",  (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW",   (0, 0), (-1, -1), 0.3, colors.HexColor("#dbeafe")),
                    ("VALIGN",      (0, 0), (-1, -1), "TOP"),
                ]

                # Alternating background on data rows
                for i in range(1, len(res_rows)):
                    if (i - 1) % 2 == 0:
                        tbl_style.append(("BACKGROUND", (0, i), (-1, i), C_LIGHT))

                res_tbl.setStyle(TableStyle(tbl_style))
                story.append(_RoundedFrame(res_tbl, radius=5, color=colors.HexColor("#bfdbfe")))

                # Compound results as standalone flowables so they split across pages
                for comp in pending_compounds:
                    story.append(Preformatted(comp["result_comp"], s_comp))
                    if comp.get("alternative_range_value"):
                        story.append(Spacer(1, 4))
                        story.append(Paragraph(
                            _xml_escape(comp["alternative_range_value"]).replace("\n", "<br/>"),
                            s_alt_ref,
                        ))

                story.append(Spacer(1, 8))

                # ── Gráficas de resultado ──────────────────────────
                for row in study["rows"]:
                    obj_name = row.get("graphic_object_name")
                    if not obj_name:
                        continue
                    img_buf = _fetch_graphic_image(obj_name)
                    if img_buf is None:
                        continue
                    story.append(
                        Paragraph(
                            f"<b>Gráfica – {row['test_name']}</b>",
                            ParagraphStyle("g_lbl", fontName="Helvetica-Bold",
                                           fontSize=8, textColor=C_NAVY),
                        )
                    )
                    story.append(Spacer(1, 4))
                    story.append(
                        RLImage(img_buf, width=COL_W, height=10 * cm,
                                kind="proportional")
                    )
                    story.append(Spacer(1, 8))

                # ── Firma(s) del validador ────────────────────────────────────────
                # Only render signatures at the last study of each same-validator group
                if signatures_map and _last_of_group[idx]:
                    study_sigs = signatures_map.get(study["id"], [])
                    if study_sigs:
                        sig_col_w = COL_W / max(len(study_sigs), 1)
                        sig_row = []
                        for sig_info in study_sigs:
                            sig_buf = _fetch_signature_image(sig_info["usr_Signature"])
                            cell = []
                            if sig_buf:
                                cell.append(
                                    RLImage(
                                        sig_buf,
                                        width=min(sig_col_w * 0.7, 5 * cm),
                                        height=2.5 * cm,
                                        kind="proportional",
                                    )
                                )
                            cell.append(
                                Paragraph(
                                    sig_info["user_name"],
                                    ParagraphStyle(
                                        "sig_name",
                                        fontName="Helvetica-Bold",
                                        fontSize=7,
                                        textColor=C_NAVY,
                                        alignment=TA_RIGHT,
                                    ),
                                )
                            )
                            if sig_info.get("usr_document_number"):
                                cell.append(
                                    Paragraph(
                                        sig_info["usr_document_number"],
                                        ParagraphStyle(
                                            "sig_doc",
                                            fontName="Helvetica",
                                            fontSize=7,
                                            textColor=C_GRAY,
                                            alignment=TA_RIGHT,
                                        ),
                                    )
                                )
                            sig_row.append(cell)
                        sig_tbl = Table(
                            [sig_row], colWidths=[sig_col_w] * len(study_sigs)
                        )
                        sig_tbl.setStyle(TableStyle([
                            ("ALIGN",         (0, 0), (-1, -1), "RIGHT"),
                            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING",    (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("LINEABOVE",     (0, 0), (-1, 0),  0.5, C_NAVY),
                        ]))
                        story.append(sig_tbl)
                        story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No hay resultados registrados para esta orden.", s_empty))

    # ── Generar PDF con reportlab ───────────────────────
    buf = io.BytesIO()

    def _draw_watermark(canvas):
        """Dibuja la marca de agua en la página actual"""
        canvas.saveState()
        wm = ImageReader(_get_watermark())
        WM_W, WM_H = 250, 100
        canvas.drawImage(wm, 0, PAGE_H - WM_H, width=WM_W, height=WM_H, mask="auto")
        canvas.drawImage(wm, PAGE_W - WM_W, (PAGE_H - WM_H) / 2, width=WM_W, height=WM_H, mask="auto")
        canvas.drawImage(wm, 0, 0, width=WM_W, height=WM_H, mask="auto")
        canvas.restoreState()

    def _draw_header(canvas):
        """Dibuja la cabecera (logo + datos del paciente) en la página actual"""
        canvas.saveState()
        
        # ── Cabecera superior (logo + PANTHOSOFT LAB) ──
        # Logo izquierda
        logo = header_data['logo']
        logo_width = 4.7 * cm  # Aumenta o disminuye este valor según necesites
        logo_height = 2.8 * cm # Aumenta o disminuye este valor según necesites
        # Si disminuyes el 2.2 (ej. 2.0), el logo sube. Si lo aumentas (ej. 2.4), el logo baja.
        canvas.drawImage(logo, LEFT, PAGE_H - 3.3 * cm, width=logo_width, height=logo_height, mask="auto")

        # Logo derecha (Azul)
        logo_blue = header_data['logo_blue']
        # Calculamos la posición X restando el ancho del logo al borde derecho (PAGE_W - RIGHT)
        canvas.drawImage(logo_blue, PAGE_W - RIGHT - logo_width, PAGE_H - 3.3 * cm, width=logo_width, height=logo_height, mask="auto")
        
        # Texto derecha (PANTHOSOFT LAB)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(C_NAVY)
        canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 1.8 * cm, "")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(C_GRAY)
        #canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 2.3 * cm, "Resultados de Laboratorio")
        
        # # Franja decorativa azul
        # canvas.setFillColor(C_NAVY)
        # canvas.rect(LEFT, PAGE_H - 2.5 * cm, COL_W, 0.15 * cm, fill=1, stroke=0)
        
        # ── Información del paciente ──
        # Título
        canvas.setFillColor(C_NAVY)
        canvas.rect(LEFT, PAGE_H - 3.2 * cm, COL_W, 0.4 * cm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(LEFT + 0.2 * cm, PAGE_H - 3.05 * cm, "INFORMACIÓN DEL PACIENTE")
        
        # Datos del paciente
        y_start = PAGE_H - 3.7 * cm
        line_height = 0.4 * cm
        
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(C_NAVY)
        
        # Fila 1: NOMBRE DEL PACIENTE
        canvas.drawString(LEFT + 0.2 * cm, y_start, "PACIENTE")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(C_DARK)
        canvas.drawString(LEFT + 2.5 * cm, y_start, header_data['patient_name'])
        
        # Fila 2: DOCUMENTO, N° ORDEN
        y = y_start - line_height
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(C_NAVY)
        canvas.drawString(LEFT + 0.2 * cm, y, "DOCUMENTO")
        canvas.drawString(LEFT + 8.5 * cm, y, "N° ORDEN")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(C_DARK)
        canvas.drawString(LEFT + 2.5 * cm, y, header_data['patient_doc'])
        canvas.drawString(LEFT + 10.5 * cm, y, header_data['order_number'])
        
        # Fila 3: EMPRESA, EDAD
        y = y - line_height
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(C_NAVY)
        canvas.drawString(LEFT + 0.2 * cm, y, "EMPRESA")
        canvas.drawString(LEFT + 8.5 * cm, y, "EDAD")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(C_DARK)
        canvas.drawString(LEFT + 2.5 * cm, y, header_data['enterprise'])
        canvas.drawString(LEFT + 10.5 * cm, y, header_data['age'])
        
        # Fila 4: MUNICIPIO, GÉNERO
        y = y - line_height
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(C_NAVY)
        canvas.drawString(LEFT + 0.2 * cm, y, "MUNICIPIO")
        canvas.drawString(LEFT + 8.5 * cm, y, "GÉNERO")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(C_DARK)
        canvas.drawString(LEFT + 2.5 * cm, y, header_data['city_name'])
        canvas.drawString(LEFT + 10.5 * cm, y, header_data['sex'])
        
        # Fila 5: SERVICIO, FECHA INGRESO
        y = y - line_height
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(C_NAVY)
        canvas.drawString(LEFT + 0.2 * cm, y, "SERVICIO")
        canvas.drawString(LEFT + 8.5 * cm, y, "FECHA INGRESO")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(C_DARK)
        canvas.drawString(LEFT + 2.5 * cm, y, header_data['service_name'])
        canvas.drawString(LEFT + 10.9 * cm, y, header_data['order_date'])
        
        # Fila 6: FECHA IMPRESIÓN
        y = y - line_height
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(C_NAVY)
        canvas.drawString(LEFT + 8.5 * cm, y, "FECHA IMPRESIÓN")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(C_DARK)
        canvas.drawString(LEFT + 10.9 * cm, y, header_data['print_date'])
        
        # Línea divisoria
        canvas.setStrokeColor(colors.HexColor("#bfdbfe"))
        canvas.setLineWidth(0.5)
        canvas.roundRect(LEFT, PAGE_H - 6.0 * cm, COL_W, 2.8 * cm, 5, fill=0, stroke=1)
        
        canvas.restoreState()

    def _draw_footer(canvas, doc):
        """Dibuja el footer en la página actual"""
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(C_GRAY)
        canvas.drawString(LEFT, 0.8 * cm, f"Generado por: LisCore · Sistema LIS · {generation_date}")
        canvas.drawRightString(PAGE_W - RIGHT, 0.8 * cm, f"Página {doc.page}")
        canvas.setStrokeColor(C_NAVY)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT, 1.1 * cm, PAGE_W - RIGHT, 1.1 * cm)
        canvas.restoreState()

    def _draw_page(canvas, doc):
        """Dibuja todos los elementos que se repiten en CADA página"""
        _draw_watermark(canvas)
        _draw_header(canvas)
        _draw_footer(canvas, doc)

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=LEFT,
        rightMargin=RIGHT,
        topMargin=TOP,
        bottomMargin=BOT,
    )
    
    # Usamos la misma función para todas las páginas
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)

    return buf.getvalue()


# ─────────────────────────────────────────────
# Agrupar laboratorios por estudio
# ─────────────────────────────────────────────
def _group_by_study(laboratories: list, is_female: bool) -> list[dict]:
    wg_groups: dict[str, dict] = {}
    wg_order: list[str] = []

    for lab in laboratories:
        study_name = "Sin estudio asignado"
        wg_name = "Sin grupo"
        if lab.order_detail and lab.order_detail.study:
            study = lab.order_detail.study
            study_name = study.name
            if study.work_group:
                wg_name = study.work_group.wg_name

        if wg_name not in wg_groups:
            wg_groups[wg_name] = {"studies": {}, "study_order": []}
            wg_order.append(wg_name)

        wg = wg_groups[wg_name]
        if study_name not in wg["studies"]:
            wg["studies"][study_name] = {"id": study.id if lab.order_detail and lab.order_detail.study else None, "labs": []}
            wg["study_order"].append(study_name)
        wg["studies"][study_name]["labs"].append(lab)

    result = []
    for wg_name in wg_order:
        wg = wg_groups[wg_name]
        studies = []
        for study_name in wg["study_order"]:
            entry = wg["studies"][study_name]
            rows = [_build_row(lab, is_female) for lab in entry["labs"]]
            studies.append({"name": study_name, "id": entry["id"], "rows": rows})
        result.append({"wg_name": wg_name, "studies": studies})

    return result


def _build_row(lab: Any, is_female: bool) -> dict:
    test = lab.test
    test_name = test.name if test else "—"
    units = (test.units or "") if test and test.units else ""
    result = _format_result(lab)
    reference = _format_reference(lab, test, is_female)
    state_label, state_class = LAB_STATE_LABELS.get(
        lab.l_state, (str(lab.l_state) if lab.l_state is not None else "—", "pendiente")
    )
    is_abnormal = _is_abnormal(lab, is_female)

    return {
        "test_name": test_name,
        "result": result,
        "units": units,
        "reference": reference,
        "state_label": state_label,
        "state_class": state_class,
        "is_abnormal": is_abnormal,
        "note": lab.l_nota_validation or "",
        "graphic_object_name": lab.l_result_graphic or None,
        "result_comp": lab.l_result_comp or "",
        "alternative_range_value": (lab.test.alternative_range_value or "") if lab.test else "",
    }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _full_name(patient: Any) -> str:
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
    test = lab.test
    # l_result tiene precedencia: si hay texto, mostrarlo tal cual (ej. "Negativo", "Positivo", "+++")
    if lab.l_result:
        return lab.l_result
    # Solo usar l_result_num si l_result está vacío
    if lab.l_result_num is not None:
        decimals = getattr(test, "num_decimal_result", None) if test and getattr(test, "test_type", None) == "N" else None
        if decimals is not None:
            return f"{float(lab.l_result_num):.{decimals}f}"
        return str(lab.l_result_num)
    # l_result_comp se muestra debajo del examen como fila compuesta, no en esta columna
    return "—"


def _format_reference(lab: Any, test: Any, is_female: bool) -> str:
    # 1. Prioridad: rangos evaluados por el sistema de RangesReferences
    ref_min = lab.__dict__.get("_ref_min")
    ref_max = lab.__dict__.get("_ref_max")
    if ref_min is not None or ref_max is not None:
        if ref_min is not None and ref_max is not None:
            return f"{ref_min} – {ref_max}"
        if ref_min is not None:
            return f">= {ref_min}"
        return f"<= {ref_max}"

    # 2. Fallback: campos legacy del TestsLab
    if not test:
        return "—"
    lo = test.female_value_min if is_female else test.male_value_min
    hi = test.female_value_max if is_female else test.male_value_max
    if lo is not None and hi is not None:
        return f"{lo} – {hi}"
    if lo is not None:
        return f">= {lo}"
    if hi is not None:
        return f"<= {hi}"
    return "—"


def _is_abnormal(lab: Any, is_female: bool = False) -> bool:
    if not lab.test:
        return False
    test = lab.test
    val = None
    # Si el resultado es texto, no se puede evaluar como anormal
    if lab.l_result:
        try:
            val = float(str(lab.l_result).replace(",", "."))
        except (ValueError, AttributeError):
            return False  # resultado textual como "Negativo", no aplica anormal
    elif lab.l_result_num is not None:
        val = float(lab.l_result_num)
    else:
        return False

    # 1. Prioridad: rangos evaluados por el sistema de RangesReferences
    ref_min = lab.__dict__.get("_ref_min")
    ref_max = lab.__dict__.get("_ref_max")
    if ref_min is not None or ref_max is not None:
        lo = float(ref_min) if ref_min is not None else None
        hi = float(ref_max) if ref_max is not None else None
    else:
        # 2. Fallback: rangos legacy del TestsLab según sexo
        lo = float(test.female_value_min) if is_female and test.female_value_min is not None else (
            float(test.male_value_min) if not is_female and test.male_value_min is not None else None
        )
        hi = float(test.female_value_max) if is_female and test.female_value_max is not None else (
            float(test.male_value_max) if not is_female and test.male_value_max is not None else None
        )

    if lo is not None and val < lo:
        return True
    if hi is not None and val > hi:
        return True
    return False


# ─────────────────────────────────────────────
# PDF Merge
# ─────────────────────────────────────────────
def merge_pdfs(main_pdf: bytes, annex_pdfs: list[bytes]) -> bytes:
    """Merge the main PDF with a list of annexed PDFs into a single PDF."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    reader = PdfReader(io.BytesIO(main_pdf))
    for page in reader.pages:
        writer.add_page(page)

    for annex_bytes in annex_pdfs:
        annex_reader = PdfReader(io.BytesIO(annex_bytes))
        for page in annex_reader.pages:
            writer.add_page(page)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────
# Encoder Base64
# ─────────────────────────────────────────────
def pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")

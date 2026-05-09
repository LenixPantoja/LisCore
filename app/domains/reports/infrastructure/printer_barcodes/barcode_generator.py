"""
PDF generator for barcode tube stickers.

Reference layout (landscape 100 mm × 40 mm):

  ┌──────────┬─────────────────────────────────────────────┬────────────┐
  │          │  LENIX ALDAIR PANTOJA  VELASQUEZ (bold)     │            │
  │  QUIMICA │  IDENTIFICACION: 1007736480                 │ 03030503   │
  │ (vertical│  EMPRESA: CLINIZAD               EDAD:25 A  │ -22        │
  │  bottom→ │  ████████████████████████████████████████   │ (vertical) │
  │   top)   │  -COL-HDL-INDI-LDLD-TRI-VLDL  - SUERO     │            │
  └──────────┴─────────────────────────────────────────────┴────────────┘
  │ EMPRESA: CLINIZAD       EDAD: 25 A   │  ← inline
  │ QUIMICA                              │  ← work group, bold
  │ ████████████████████████████         │  ← Code128 barcode
  │ -COL-HDL-INDI-LDLD-TRI-VLDL         │  ← tests abbreviations
  │                         03030503-22  │  ← right-aligned order-suffix
  └──────────────────────────────────────┘
"""
import base64
import io
from typing import List

from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.units import mm
from reportlab.lib.colors import black, Color

# Negro puro CMYK (K=100%) → máximo contraste en impresoras térmicas
PURE_BLACK = Color(0, 0, 0, 1)

# ── Sticker dimensions ─────────────────────────────────────────────────────
STICKER_W   = 50 * mm
STICKER_H   = 25 * mm

LEFT_COL_W  = 6   * mm   # left strip  → work group (vertical)
RIGHT_COL_W = 7   * mm   # right strip → order-suffix label (vertical)
H_MARGIN_L  = 4.5 * mm   # inner left margin  (increased to avoid printer clipping)
H_MARGIN_R  = 1.5 * mm   # inner right margin

CONTENT_X = LEFT_COL_W + H_MARGIN_L
CONTENT_R = STICKER_W - RIGHT_COL_W - H_MARGIN_R
CONTENT_W = CONTENT_R - CONTENT_X

F_BOLD   = "Helvetica-Bold"
F_NORMAL = "Helvetica"


def _fit(c, text: str, font: str, size: float, max_w: float) -> str:
    """Truncate text with '…' to fit within max_w points."""
    if c.stringWidth(text, font, size) <= max_w:
        return text
    while text:
        candidate = text[:-1] + "…"
        if c.stringWidth(candidate, font, size) <= max_w:
            return candidate
        text = text[:-1]
    return "…"


def _vertical(c, x_center: float, y_center: float,
              text: str, font: str, size: float, max_h: float) -> None:
    """Draw text rotated 90° (reads bottom→top), centred at (x_center, y_center)."""
    c.saveState()
    c.translate(x_center, y_center)
    c.rotate(90)
    c.setFont(font, size)
    fitted = _fit(c, text, font, size, max_h - 3 * mm)
    c.drawCentredString(0, -size * 0.35, fitted)
    c.restoreState()


def _draw_sticker(c, sticker: dict) -> None:
    W, H = STICKER_W, STICKER_H

    # ── Vertical separator lines ─────────────────────────────────────────────
    c.setStrokeColor(PURE_BLACK)
    c.setLineWidth(0.4)
    c.line(LEFT_COL_W,      0, LEFT_COL_W,      H)
    c.line(W - RIGHT_COL_W, 0, W - RIGHT_COL_W, H)

    # ── Left strip: Work Group ───────────────────────────────────────────────
    _vertical(c,
              x_center=LEFT_COL_W / 2,
              y_center=H / 2,
              text=sticker["work_group_name"],
              font=F_BOLD, size=6, max_h=H)

    # ── Right strip: Label Number ────────────────────────────────────────────
    _vertical(c,
              x_center=W - RIGHT_COL_W / 2,
              y_center=H / 2,
              text=sticker["label_number"],
              font=F_BOLD, size=5.5, max_h=H)

    # ── Content area ─────────────────────────────────────────────────────────
    c.setFillColor(PURE_BLACK)

    # Y positions: información del paciente + código de barras en la parte
    # superior; línea de estudios centrada en el espacio inferior.
    y_patient  = H - 3.5 * mm            # nombre paciente (baseline)
    y_ident    = y_patient - 2.2 * mm    # identificación
    y_empresa  = y_ident   - 2.0 * mm    # empresa / edad
    bc_h       = 8 * mm
    y_bc_top   = y_empresa - 1.2 * mm
    y_bc_bot   = y_bc_top  - bc_h
    y_sample    = 1.0 * mm               # tipo de muestra (línea inferior)
    y_tests    = y_sample + 2.0 * mm      # códigos de estudios (sobre el tipo de muestra)

    # Patient name
    c.setFont(F_BOLD, 5.5)
    name = _fit(c, sticker["patient_full_name"], F_BOLD, 5.5, CONTENT_W)
    c.drawString(CONTENT_X, y_patient, name)

    # Identification
    c.setFont(F_NORMAL, 5)
    c.drawString(CONTENT_X, y_ident,
                 f"IDENTIFICACION: {sticker['identification']}")

    # Empresa (left) + Edad (right-aligned) — misma línea
    c.setFont(F_NORMAL, 5)
    c.drawString(CONTENT_X, y_empresa,
                 f"EMPRESA: {sticker['enterprise_name']}")
    c.setFont(F_NORMAL, 5)
    c.drawRightString(CONTENT_R, y_empresa, f"EDAD: {sticker['age_str']}")

    # Barcode Code128
    bv = sticker["barcode_value"]
    try:
        bc = code128.Code128(
            bv,
            barWidth=1.2,
            barHeight=bc_h,
            humanReadable=False,
            quiet=False,
        )
        # Anclar desde CONTENT_X, escalar si excede el ancho disponible
        if bc.width > CONTENT_W:
            scale = CONTENT_W / bc.width
            c.saveState()
            c.translate(CONTENT_X, y_bc_bot)
            c.scale(scale, 1)
            bc.drawOn(c, 0, 0)
            c.restoreState()
        else:
            bc_x = CONTENT_X + max(0.0, (CONTENT_W - bc.width) / 2)
            bc.drawOn(c, bc_x, y_bc_bot)
    except Exception:
        c.setFont(F_NORMAL, 5)
        c.drawCentredString(CONTENT_X + CONTENT_W / 2,
                            y_bc_bot + bc_h / 2, f"[{bv}]")

    # Tests line (study codes)
    c.setFont(F_BOLD, 5)
    tl = _fit(c, sticker["tests_line"], F_BOLD, 5, CONTENT_W)
    c.drawString(CONTENT_X, y_tests, tl)

    # Sample type (below tests line)
    c.setFont(F_NORMAL, 5)
    st_name = _fit(c, sticker.get("sample_type_name", ""), F_NORMAL, 5, CONTENT_W)
    c.drawString(CONTENT_X, y_sample, st_name)


def build_stickers_pdf(stickers: List[dict]) -> bytes:
    """One sticker per page (100 mm × 40 mm)."""
    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=(STICKER_W, STICKER_H))
    for sticker in stickers:
        _draw_sticker(c, sticker)
        c.showPage()
    c.save()
    return buf.getvalue()


def pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")

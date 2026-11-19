"""
Exportar e importar el tarifario (valores por estudio de una tarifa) en Excel.

Exportar: un libro con todos los estudios activos (y los inactivos que ya están
en la tarifa) con su valor; los que no están en la tarifa salen con el valor
vacío.

Importar: se lee el mismo formato y, por cada fila con valor:
  - si el estudio ya está en la tarifa y el valor cambió  -> se actualiza
  - si el estudio no está en la tarifa                    -> se agrega
  - si el valor es igual                                  -> sin cambios
Las filas con el valor vacío se ignoran: la importación NUNCA elimina estudios
de la tarifa. El estudio se identifica por la columna "ID" (oculta en el
archivo) y, si falta, por el código del estudio.

Con dry_run=True solo se calcula el resumen (vista previa) sin guardar nada.
"""
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.contractstariffs.domain.models import Tariff, TariffDetail
from app.domains.studieslab.domain.models import StudiesLab

HEADERS = ["ID", "Código", "CUPS", "Estudio", "Estado", "Valor"]
SHEET = "Tarifario"
MAX_ROWS = 20000
MAX_VALUE = Decimal("999999999999")


async def _get_tariff(db: AsyncSession, tariff_id: int) -> Tariff:
    tariff = await db.get(Tariff, tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarifa no existe.")
    return tariff


def _safe_filename(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "tarifa").strip()).strip("_") or "tarifa"
    return f"Tarifario_{base}_{datetime.now().strftime('%Y%m%d')}.xlsx"


# ─────────────────────────── Exportar ───────────────────────────

async def export_tariff_excel(db: AsyncSession, tariff_id: int) -> tuple[bytes, str]:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    from openpyxl.worksheet.datavalidation import DataValidation

    tariff = await _get_tariff(db, tariff_id)

    # Valor actual por estudio (si hubiera duplicados se toma el primero)
    values: dict[int, Decimal] = {}
    for td in (await db.execute(
        select(TariffDetail).where(TariffDetail.td_tariff_id == tariff_id).order_by(TariffDetail.td_id)
    )).scalars().all():
        if td.td_studie_id is not None and td.td_studie_id not in values:
            values[td.td_studie_id] = td.td_value

    studies = (await db.execute(
        select(StudiesLab)
        .where(or_(StudiesLab.active.is_(True), StudiesLab.id.in_(list(values.keys()) or [-1])))
        .order_by(StudiesLab.code, StudiesLab.id)
    )).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = SHEET

    dark = PatternFill("solid", fgColor="1E293B")
    soft = PatternFill("solid", fgColor="F1F5F9")
    thin = Side(style="thin", color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"] = f"Tarifario: {tariff.t_name}"
    ws["A1"].font = Font(bold=True, size=13, color="1E293B")
    ws["A2"] = (
        "Modifique solo la columna Valor. Deje el valor vacío para no incluir el estudio. "
        "No cambie la columna ID ni el orden de las columnas. La importación no elimina estudios de la tarifa."
    )
    ws["A2"].font = Font(italic=True, size=9, color="64748B")
    ws.merge_cells("A1:F1")
    ws.merge_cells("A2:F2")

    header_row = 4
    for col, title in enumerate(HEADERS, start=1):
        c = ws.cell(row=header_row, column=col, value=title)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = dark
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border

    row = header_row + 1
    for s in studies:
        val = values.get(s.id)
        cells = [
            s.id,
            s.code or "",
            (s.cups_code or "") if (s.cups_code or "").upper() != "NULL" else "",
            s.name or "",
            "Activo" if s.active else "Inactivo",
            float(val) if val is not None else None,
        ]
        for col, v in enumerate(cells, start=1):
            c = ws.cell(row=row, column=col, value=v)
            c.border = border
            if col in (1, 2, 3, 4, 5):
                c.fill = soft if val is None else PatternFill(fill_type=None)
        ws.cell(row=row, column=6).number_format = '"$"#,##0'
        row += 1

    # Valor: número >= 0
    if row > header_row + 1:
        dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True,
                            showErrorMessage=True, errorTitle="Valor no válido",
                            error="Ingrese un valor numérico mayor o igual a cero.")
        ws.add_data_validation(dv)
        dv.add(f"F{header_row + 1}:F{row - 1}")

    widths = {"A": 8, "B": 16, "C": 14, "D": 70, "E": 11, "F": 16}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws.column_dimensions["A"].hidden = True  # ID: clave para la importación
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    ws.auto_filter.ref = f"A{header_row}:F{max(row - 1, header_row)}"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), _safe_filename(tariff.t_name)


# ─────────────────────────── Importar ───────────────────────────

def _parse_value(raw) -> tuple[Optional[Decimal], Optional[str]]:
    """(valor, error). Vacío -> (None, None)."""
    if raw is None:
        return None, None
    if isinstance(raw, bool):
        return None, "valor no numérico"
    if isinstance(raw, (int, float, Decimal)):
        try:
            v = Decimal(str(raw))
        except InvalidOperation:
            return None, "valor no numérico"
    else:
        s = str(raw).strip().replace("$", "").replace(" ", "").replace(" ", "")
        if not s or s in ("-", "—"):
            return None, None
        if "," in s and "." in s:
            # 12.500,50 (punto miles) o 12,500.50 (coma miles): el último separador es el decimal
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            parts = s.split(",")
            s = s.replace(",", "") if len(parts) > 2 or len(parts[-1]) == 3 else s.replace(",", ".")
        elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[-1]) == 3):
            s = s.replace(".", "")
        try:
            v = Decimal(s)
        except InvalidOperation:
            return None, f"valor no numérico ('{raw}')"
    if v < 0:
        return None, "el valor no puede ser negativo"
    if v > MAX_VALUE:
        return None, "el valor es demasiado grande"
    return v.quantize(Decimal("0.01")), None


def _find_header(ws) -> tuple[int, dict[str, int]]:
    """Fila de encabezados y posición de cada columna (busca en las primeras 15 filas)."""
    norm = lambda x: re.sub(r"\s+", " ", str(x or "")).strip().lower()
    wanted = {"id": "id", "código": "code", "codigo": "code", "cups": "cups", "estudio": "name", "valor": "value"}
    for r in range(1, 16):
        found: dict[str, int] = {}
        for c in range(1, 15):
            key = wanted.get(norm(ws.cell(row=r, column=c).value))
            if key and key not in found:
                found[key] = c
        if "value" in found and ("id" in found or "code" in found):
            return r, found
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="El archivo no tiene el formato del tarifario. Exporte el tarifario y use ese archivo para importar.",
    )


async def import_tariff_excel(db: AsyncSession, tariff_id: int, content: bytes, dry_run: bool = True) -> dict:
    from openpyxl import load_workbook

    tariff = await _get_tariff(db, tariff_id)
    tariff_name = tariff.t_name
    try:
        wb = load_workbook(io.BytesIO(content), data_only=True, read_only=False)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudo leer el archivo. Verifique que sea un Excel (.xlsx) exportado desde el tarifario.",
        )
    ws = wb[SHEET] if SHEET in wb.sheetnames else wb.active
    header_row, cols = _find_header(ws)

    if ws.max_row - header_row > MAX_ROWS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"El archivo supera el máximo de {MAX_ROWS} filas.")

    # Catálogo de estudios y detalles actuales
    studies = (await db.execute(select(StudiesLab.id, StudiesLab.code, StudiesLab.name))).all()
    by_id = {s.id: s for s in studies}
    by_code: dict[str, list] = {}
    for s in studies:
        if s.code:
            by_code.setdefault(s.code.strip().upper(), []).append(s)

    # Valores actuales por estudio (un estudio puede tener filas repetidas en la tarifa)
    current: dict[int, list[Decimal]] = {}
    for sid, val in (await db.execute(
        select(TariffDetail.td_studie_id, TariffDetail.td_value)
        .where(TariffDetail.td_tariff_id == tariff_id)
        .order_by(TariffDetail.td_id)
    )).all():
        if sid is not None:
            current.setdefault(sid, []).append(Decimal(str(val if val is not None else 0)).quantize(Decimal("0.01")))
    to_update: list[tuple[int, Decimal]] = []
    to_add: list[tuple[int, Decimal]] = []

    updated, added, errors = [], [], []
    unchanged = skipped = 0
    seen: set[int] = set()

    for r in range(header_row + 1, ws.max_row + 1):
        get = lambda k: ws.cell(row=r, column=cols[k]).value if k in cols else None
        raw_id, raw_code, raw_value = get("id"), get("code"), get("value")
        if raw_id in (None, "") and raw_code in (None, "") and raw_value in (None, ""):
            continue  # fila vacía

        code_txt = str(raw_code).strip() if raw_code not in (None, "") else ""
        label = code_txt or (str(raw_id) if raw_id not in (None, "") else f"fila {r}")

        value, err = _parse_value(raw_value)
        if err:
            errors.append({"row": r, "study": label, "message": err})
            continue
        if value is None:
            skipped += 1
            continue

        # Identificar el estudio: por ID y, si no, por código
        study = None
        if raw_id not in (None, ""):
            try:
                study = by_id.get(int(float(str(raw_id).strip())))
            except ValueError:
                study = None
            if study and code_txt and (study.code or "").strip().upper() != code_txt.upper():
                errors.append({"row": r, "study": label,
                               "message": "el ID y el código no corresponden al mismo estudio"})
                continue
        if study is None and code_txt:
            matches = by_code.get(code_txt.upper(), [])
            if len(matches) > 1:
                errors.append({"row": r, "study": label, "message": "hay varios estudios con ese código"})
                continue
            study = matches[0] if matches else None
        if study is None:
            errors.append({"row": r, "study": label, "message": "el estudio no existe en el sistema"})
            continue
        if study.id in seen:
            errors.append({"row": r, "study": label, "message": "el estudio está repetido en el archivo"})
            continue
        seen.add(study.id)

        olds = current.get(study.id)
        item = {"study_id": study.id, "code": study.code, "name": study.name, "new_value": float(value)}
        if olds is None:
            added.append({**item, "old_value": None})
            to_add.append((study.id, value))
        elif any(o != value for o in olds):
            updated.append({**item, "old_value": float(olds[0])})
            to_update.append((study.id, value))
        else:
            unchanged += 1

    if not dry_run and (to_update or to_add):
        from sqlalchemy import update as sa_update
        # Se actualizan TODAS las filas del estudio en la tarifa (incluidas las repetidas)
        for sid, val in to_update:
            await db.execute(
                sa_update(TariffDetail)
                .where(TariffDetail.td_tariff_id == tariff_id, TariffDetail.td_studie_id == sid)
                .values(td_value=val)
            )
        for sid, val in to_add:
            db.add(TariffDetail(td_tariff_id=tariff_id, td_studie_id=sid, td_value=val))
        await db.commit()

    return {
        "tariff_id": tariff_id,
        "tariff_name": tariff_name,
        "dry_run": dry_run,
        "updated_count": len(updated),
        "added_count": len(added),
        "unchanged_count": unchanged,
        "skipped_count": skipped,
        "error_count": len(errors),
        "updated": updated[:300],
        "added": added[:300],
        "errors": errors[:300],
    }

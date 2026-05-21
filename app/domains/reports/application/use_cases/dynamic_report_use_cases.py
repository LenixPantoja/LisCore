import base64
import io
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from jinja2 import Template, TemplateError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.reports.domain.dynamic_report_models import DynamicReport, ReportParameter
from app.domains.reports.infrastructure.dynamic_report_repository import DynamicReportRepository


def _html_to_pdf_bytes(
    html_content: str,
    page_size: str = "carta",
    orientation: str = "portrait",
) -> bytes:
    """Convert an HTML string to PDF bytes using xhtml2pdf (no system libs required).

    Supported page sizes: 'carta' (letter 8.5×11in), 'oficio' (legal 8.5×14in).
    Supported orientations: 'portrait', 'landscape'.
    """
    try:
        from xhtml2pdf import pisa  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="xhtml2pdf no está instalado. No es posible exportar a PDF.",
        ) from exc

    _size_map = {
        "carta": "letter",
        "oficio": "legal",
    }
    css_size = _size_map.get(page_size, "letter")
    page_css = (
        f"<style>@page {{ size: {css_size} {orientation}; "
        f"margin: 1.5cm; }}</style>\n"
    )
    html_with_page = page_css + html_content

    buf = io.BytesIO()
    status_obj = pisa.CreatePDF(html_with_page, dest=buf, encoding="utf-8")
    if status_obj.err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el PDF (xhtml2pdf): {status_obj.err}",
        )
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _resolve_parameter_options(
    db: AsyncSession, param: ReportParameter
) -> Optional[List[Dict[str, Any]]]:
    """If the parameter has a source_query, execute it and return option list."""
    if param.rp_source_query:
        rows = await DynamicReportRepository.execute_source_query(db, param.rp_source_query)
        # Expect columns: value, label (first two columns as fallback)
        options = []
        for row in rows:
            keys = list(row.keys())
            options.append({
                "value": row[keys[0]],
                "label": row[keys[1]] if len(keys) > 1 else str(row[keys[0]]),
            })
        return options
    return None


def _render_html(template_str: str, data: List[dict], params: dict) -> str:
    """Render a Jinja2 HTML template with report data and filter params."""
    try:
        template = Template(template_str)
        return template.render(data=data, params=params)
    except TemplateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al renderizar la plantilla HTML: {exc}",
        )


def _coerce_params(
    raw_params: dict, param_definitions: List[ReportParameter]
) -> dict:
    """Convert raw string values to proper Python types based on rp_type definitions.

    asyncpg requires typed Python objects (date, datetime, int, float) — not plain strings.
    """
    type_map = {p.rp_name: p.rp_type for p in param_definitions}
    coerced: dict = {}

    for key, value in raw_params.items():
        if value is None:
            coerced[key] = value
            continue

        param_type = type_map.get(key, "text")

        if param_type == "date" and isinstance(value, str):
            try:
                coerced[key] = date.fromisoformat(value)
            except ValueError:
                coerced[key] = value

        elif param_type == "datetime" and isinstance(value, str):
            try:
                coerced[key] = datetime.fromisoformat(value)
            except ValueError:
                coerced[key] = value

        elif param_type == "number" and isinstance(value, str):
            try:
                coerced[key] = int(value) if "." not in value else float(value)
            except ValueError:
                coerced[key] = value

        elif param_type in ("select", "multiselect") and isinstance(value, str):
            # If the value looks like an integer (e.g. a foreign-key id), coerce it
            # so asyncpg does not receive a string where the DB column is INTEGER.
            try:
                coerced[key] = int(value)
            except ValueError:
                try:
                    coerced[key] = float(value)
                except ValueError:
                    coerced[key] = value  # leave as text (e.g. a code string)

        else:
            coerced[key] = value

    return coerced


# ---------------------------------------------------------------------------
# Use cases
# ---------------------------------------------------------------------------

async def list_reports(db: AsyncSession) -> List[DynamicReport]:
    return list(await DynamicReportRepository.list_all(db))


async def list_reports_tree(db: AsyncSession) -> List[Dict[str, Any]]:
    """Return active reports grouped by category as a tree structure.

    Reports without a category appear under the key ``None``.
    Within each category, reports are sorted alphabetically.
    """
    reports = await DynamicReportRepository.list_all(db)

    # Preserve insertion order so categories appear in the order they are first seen
    groups: Dict[Optional[str], List[Dict[str, Any]]] = {}
    for report in reports:
        category = report.dr_category_name or None
        if category not in groups:
            groups[category] = []
        groups[category].append({
            "dr_id": report.dr_id,
            "dr_name": report.dr_name,
            "dr_description": report.dr_description,
            "dr_active": report.dr_active,
        })

    return [{"category": cat, "reports": items} for cat, items in groups.items()]


async def get_report_detail(db: AsyncSession, report_id: int) -> Dict[str, Any]:
    """Return the report metadata together with each parameter's options resolved."""
    report = await DynamicReportRepository.get_by_id(db, report_id)

    resolved_params = []
    for param in report.parameters:
        entry: Dict[str, Any] = {
            "rp_id": param.rp_id,
            "rp_name": param.rp_name,
            "rp_label": param.rp_label,
            "rp_type": param.rp_type,
            "rp_required": param.rp_required,
            "rp_default_value": param.rp_default_value,
            "rp_order_index": param.rp_order_index,
            "options": None,
        }
        if param.rp_type in ("select", "multiselect"):
            entry["options"] = await _resolve_parameter_options(db, param)
        resolved_params.append(entry)

    return {
        "dr_id": report.dr_id,
        "dr_name": report.dr_name,
        "dr_description": report.dr_description,
        "dr_active": report.dr_active,
        "parameters": resolved_params,
    }


async def create_report(
    db: AsyncSession,
    report_data: dict,
    params_data: List[dict],
) -> DynamicReport:
    report = await DynamicReportRepository.create(db, report_data, params_data)
    await db.commit()
    await db.refresh(report)
    return report


async def update_report(
    db: AsyncSession,
    report_id: int,
    report_data: dict,
    params_data: Optional[List[dict]],
) -> DynamicReport:
    report = await DynamicReportRepository.update(db, report_id, report_data, params_data)
    await db.commit()
    await db.refresh(report)
    return report


async def delete_report(db: AsyncSession, report_id: int) -> None:
    await DynamicReportRepository.soft_delete(db, report_id)
    await db.commit()


async def run_report(
    db: AsyncSession,
    report_id: int,
    filter_params: dict,
) -> Dict[str, Any]:
    """Execute the report SQL with the provided filters and render HTML."""
    report = await DynamicReportRepository.get_by_id(db, report_id)

    # Validate required parameters are present
    for param in report.parameters:
        if param.rp_required and param.rp_name not in filter_params:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El parámetro requerido '{param.rp_label}' no fue enviado.",
            )

    # Coerce string values to proper Python types for asyncpg
    typed_params = _coerce_params(filter_params, report.parameters)

    data_rows = await DynamicReportRepository.execute_report_query(
        db, report.dr_sql_query, typed_params
    )
    html = _render_html(report.dr_html_template, data_rows, filter_params)

    return {
        "report_id": report.dr_id,
        "report_name": report.dr_name,
        "total_rows": len(data_rows),
        "html": html,
    }


async def export_report_pdf(
    db: AsyncSession,
    report_id: int,
    filter_params: dict,
    page_size: str = "carta",
    orientation: str = "portrait",
) -> Dict[str, Any]:
    """Run the report and convert the rendered HTML to PDF (base64-encoded).

    Args:
        page_size: 'carta' (letter) or 'oficio' (legal).
        orientation: 'portrait' or 'landscape'.
    """
    result = await run_report(db, report_id, filter_params)
    html_content = result["html"]

    pdf_bytes = _html_to_pdf_bytes(html_content, page_size=page_size, orientation=orientation)

    encoded = base64.b64encode(pdf_bytes).decode("utf-8")
    filename = f"reporte_{report_id}_{result['report_name'].replace(' ', '_')}.pdf"

    return {
        "filename": filename,
        "base64_pdf": encoded,
        "report_name": result["report_name"],
        "total_rows": result["total_rows"],
    }


async def export_report_xlsx(
    db: AsyncSession,
    report_id: int,
    filter_params: dict,
) -> Dict[str, Any]:
    """Run the report SQL and export the raw data rows as an XLSX file (base64-encoded)."""
    try:
        import openpyxl  # type: ignore
        from openpyxl.styles import Font, PatternFill, Alignment  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="openpyxl no está instalado. No es posible exportar a XLSX.",
        ) from exc

    report = await DynamicReportRepository.get_by_id(db, report_id)

    # Validate required parameters
    for param in report.parameters:
        if param.rp_required and param.rp_name not in filter_params:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El parámetro requerido '{param.rp_label}' no fue enviado.",
            )

    typed_params = _coerce_params(filter_params, report.parameters)
    data_rows = await DynamicReportRepository.execute_report_query(
        db, report.dr_sql_query, typed_params
    )

    # Build XLSX
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = report.dr_name[:31]  # Sheet name max 31 chars

    if data_rows:
        headers = list(data_rows[0].keys())

        # Header row styling
        header_fill = PatternFill(start_color="233248", end_color="233248", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        header_alignment = Alignment(horizontal="center", vertical="center")

        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        # Data rows
        for row_idx, row in enumerate(data_rows, start=2):
            for col_idx, key in enumerate(headers, start=1):
                value = row[key]
                # Convert date/datetime to string for Excel compatibility
                if hasattr(value, "isoformat"):
                    value = value.isoformat()
                ws.cell(row=row_idx, column=col_idx, value=value)

        # Auto-fit column widths (approximate)
        for col in ws.columns:
            max_len = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in col
            )
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    filename = f"reporte_{report_id}_{report.dr_name.replace(' ', '_')}.xlsx"

    return {
        "filename": filename,
        "base64_xlsx": encoded,
        "report_name": report.dr_name,
        "total_rows": len(data_rows),
    }

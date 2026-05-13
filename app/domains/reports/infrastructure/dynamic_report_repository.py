import logging
import re
from typing import List, Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.domains.reports.domain.dynamic_report_models import DynamicReport, ReportParameter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security: forbidden SQL statement keywords
# ---------------------------------------------------------------------------
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|EXEC|EXECUTE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def _assert_select_only(sql: str) -> None:
    """Raise HTTP 400 if *sql* contains anything other than a read-only query."""
    if _FORBIDDEN_SQL.search(sql):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten consultas SELECT en las definiciones de reportes.",
        )
    stripped = sql.strip().lstrip(";").strip().upper()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La consulta SQL debe iniciar con SELECT (o WITH para CTEs).",
        )


def _safe_db_error_message(exc: Exception) -> str:
    """Extract a user-friendly message from a DB exception without leaking SQL or params."""
    raw = str(exc)
    # asyncpg errors usually have the user-visible message before newlines or brackets
    first_line = raw.split("\n")[0]
    # Strip SQLAlchemy wrapper prefix, keep only the core DB message
    match = re.search(r"<class '[^']+'>:\s*(.+)", first_line)
    if match:
        return match.group(1).strip()
    # Fallback: take the first sentence before SQL details
    short = first_line.split("[SQL:")[0].strip()
    return short or "Error inesperado al ejecutar la consulta."


class DynamicReportRepository:
    # ------------------------------------------------------------------
    # Report CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def list_all(db: AsyncSession) -> Sequence[DynamicReport]:
        result = await db.execute(
            select(DynamicReport)
            .where(DynamicReport.dr_active == True)
            .order_by(DynamicReport.dr_category_name.nulls_last(), DynamicReport.dr_name)
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, report_id: int) -> DynamicReport:
        result = await db.execute(
            select(DynamicReport)
            .options(selectinload(DynamicReport.parameters))
            .where(DynamicReport.dr_id == report_id)
        )
        report = result.scalars().first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reporte dinámico con id={report_id} no encontrado.",
            )
        return report

    @staticmethod
    async def create(db: AsyncSession, data: dict, params: List[dict]) -> DynamicReport:
        _assert_select_only(data["dr_sql_query"])
        report = DynamicReport(**data)
        db.add(report)
        await db.flush()

        for param in params:
            if param.get("rp_source_query"):
                _assert_select_only(param["rp_source_query"])
            rp = ReportParameter(rp_report_id=report.dr_id, **param)
            db.add(rp)

        await db.flush()
        await db.refresh(report)
        return report

    @staticmethod
    async def update(
        db: AsyncSession, report_id: int, data: dict, params: Optional[List[dict]]
    ) -> DynamicReport:
        report = await DynamicReportRepository.get_by_id(db, report_id)

        if "dr_sql_query" in data:
            _assert_select_only(data["dr_sql_query"])

        for field, value in data.items():
            setattr(report, field, value)

        if params is not None:
            # Full replacement of parameters
            for rp in list(report.parameters):
                await db.delete(rp)
            await db.flush()

            for param in params:
                if param.get("rp_source_query"):
                    _assert_select_only(param["rp_source_query"])
                rp = ReportParameter(rp_report_id=report_id, **param)
                db.add(rp)

        await db.flush()
        await db.refresh(report)
        return report

    @staticmethod
    async def soft_delete(db: AsyncSession, report_id: int) -> None:
        report = await DynamicReportRepository.get_by_id(db, report_id)
        report.dr_active = False
        await db.flush()

    # ------------------------------------------------------------------
    # Dynamic SQL execution (read-only, parameterized)
    # ------------------------------------------------------------------

    @staticmethod
    async def execute_report_query(
        db: AsyncSession, sql_query: str, params: dict
    ) -> List[dict]:
        _assert_select_only(sql_query)
        # Normalize whitespace and strip trailing semicolons
        clean_sql = sql_query.strip().rstrip(";").strip()
        # Wrap in subquery so asyncpg/SQLAlchemy always recognizes a row-returning result
        wrapped = f"SELECT * FROM (\n{clean_sql}\n) AS _dynamic_report_"
        try:
            result = await db.execute(text(wrapped), params)
            rows = [dict(row) for row in result.mappings().all()]
            return rows
        except Exception as exc:
            logger.error("Error executing dynamic report query: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al ejecutar la consulta del reporte: {_safe_db_error_message(exc)}",
            )

    @staticmethod
    async def execute_source_query(db: AsyncSession, source_query: str) -> List[dict]:
        """Execute a parameter's source_query to populate select options."""
        _assert_select_only(source_query)
        clean_sql = source_query.strip().rstrip(";").strip()
        wrapped = f"SELECT * FROM (\n{clean_sql}\n) AS _source_options_"
        try:
            result = await db.execute(text(wrapped))
            rows = [dict(row) for row in result.mappings().all()]
            return rows
        except Exception as exc:
            logger.error("Error executing parameter source_query: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al ejecutar source_query de parámetro: {_safe_db_error_message(exc)}",
            )

"""Temp script: rewrite dynamic_report_models.py with the new fields."""
content = """\
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from utils.timezone import get_bogota_now


class DynamicReport(Base):
    __tablename__ = "DynamicReports"

    dr_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    dr_name = Column(String(200), nullable=False)
    dr_description = Column(Text, nullable=True)
    dr_category_name = Column(String(150), nullable=True, index=True)
    dr_sql_query = Column(Text, nullable=False)
    dr_html_template = Column(Text, nullable=False)
    dr_active = Column(Boolean, nullable=False, default=True)
    # Document control metadata shown in the PDF header
    dr_code = Column(String(50), nullable=True)
    dr_version = Column(String(20), nullable=True)
    dr_emission_date = Column(String(20), nullable=True)
    dr_created_at = Column(DateTime, default=get_bogota_now)
    dr_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    parameters = relationship(
        "ReportParameter",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportParameter.rp_order_index",
    )

    def __repr__(self) -> str:
        return f"<DynamicReport(id={self.dr_id}, name={self.dr_name!r})>"


class ReportParameter(Base):
    __tablename__ = "ReportParameters"

    rp_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    rp_report_id = Column(
        Integer, ForeignKey("DynamicReports.dr_id", ondelete="CASCADE"), nullable=False
    )
    rp_name = Column(String(100), nullable=False)
    rp_label = Column(String(100), nullable=False)
    # Allowed types: date | datetime | text | number | select | multiselect | checkbox | textarea
    rp_type = Column(String(50), nullable=False)
    rp_required = Column(Boolean, nullable=False, default=False)
    rp_default_value = Column(Text, nullable=True)
    # For select / multiselect: SQL that returns {value, label} rows
    rp_source_query = Column(Text, nullable=True)
    rp_order_index = Column(Integer, nullable=False, default=0)

    report = relationship("DynamicReport", back_populates="parameters")

    def __repr__(self) -> str:
        return f"<ReportParameter(id={self.rp_id}, name={self.rp_name!r}, type={self.rp_type!r})>"
"""

target = "app/domains/reports/domain/dynamic_report_models.py"
with open(target, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)
print(f"Written: {target}")

# Verify
from app.domains.reports.domain.dynamic_report_models import DynamicReport
cols = [c.key for c in DynamicReport.__table__.columns]
print("Columns:", cols)
assert "dr_code" in cols, "dr_code missing!"
assert "dr_version" in cols, "dr_version missing!"
assert "dr_emission_date" in cols, "dr_emission_date missing!"
print("All new columns verified OK.")

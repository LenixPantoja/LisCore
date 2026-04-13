from sqlalchemy import Column, Integer, String, Boolean, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.core.database import Base


class AnalyzerGroup(Base):
    __tablename__ = "Analyzers_Groups"

    ag_id = Column(Integer, primary_key=True, index=True)
    ag_name = Column(String(255))
    ag_active = Column(Boolean, default=True)

    analyzers = relationship("Analyzer", back_populates="group")


class Analyzer(Base):
    __tablename__ = "Analyzers"

    a_id = Column(Integer, primary_key=True, index=True)
    a_name = Column(String(255))
    a_description = Column(String(255))
    a_analyzer_group_id = Column(Integer, ForeignKey("Analyzers_Groups.ag_id"), nullable=True)
    a_work_group_id = Column(Integer, ForeignKey("Work_groups.wg_id"), nullable=True)
    a_licence = Column(Text, nullable=True)
    a_created_at = Column(DateTime, nullable=True)
    a_updated_at = Column(DateTime, nullable=True)
    a_active = Column(Boolean, default=True)

    group = relationship("AnalyzerGroup", back_populates="analyzers")
    work_group = relationship("app.domains.masters.domain.models.WorkGroup")
    details = relationship("AnalyzerDetail", back_populates="analyzer", cascade="all, delete-orphan")


class AnalyzerDetail(Base):
    __tablename__ = "AnalyzerDetails"

    ad_id = Column(Integer, primary_key=True, index=True)
    ad_analyzer_id = Column(Integer, ForeignKey("Analyzers.a_id"))
    ad_transmission_code = Column(String(255))
    ad_receipt_code_results = Column(String(255))
    ad_test_id = Column(Integer, ForeignKey("TestsLab.id"), nullable=True)
    ad_sufix = Column(String(255))
    ad_active = Column(Boolean, default=True)
    ad_created_at = Column(Date, nullable=True)
    ad_updated_at = Column(Date, nullable=True)

    analyzer = relationship("Analyzer", back_populates="details")
    test = relationship("app.domains.testslabs.domain.models.TestsLab")

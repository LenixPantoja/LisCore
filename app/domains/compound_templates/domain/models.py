from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
from utils.timezone import get_bogota_now


class CompoundTemplate(Base):
    """Plantilla de completado dinámico de resultados (ej. Panel Respiratorio FilmArray)."""

    __tablename__ = "CompoundTemplates"

    ct_id = Column(Integer, primary_key=True, index=True)
    ct_name = Column(String(255), nullable=False)
    ct_description = Column(Text, nullable=True)
    ct_template = Column(JSONB, nullable=False, default=list)
    ct_active = Column(Boolean, default=True, nullable=False)
    ct_created_at = Column(DateTime, default=get_bogota_now)
    ct_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    # Relación N:M con TestsLab
    test_links = relationship("TestCompoundTemplate", back_populates="template", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CompoundTemplate(id={self.ct_id}, name='{self.ct_name}')>"


class TestCompoundTemplate(Base):
    """Tabla pivote N:M entre TestsLab y CompoundTemplate."""

    __tablename__ = "TestCompoundTemplates"

    tct_id = Column(Integer, primary_key=True, index=True)
    tct_test_id = Column(Integer, ForeignKey("TestsLab.id", ondelete="CASCADE"), nullable=False, index=True)
    tct_template_id = Column(Integer, ForeignKey("CompoundTemplates.ct_id", ondelete="CASCADE"), nullable=False, index=True)
    tct_is_default = Column(Boolean, default=False, nullable=False)
    tct_order_index = Column(Integer, default=0, nullable=False)
    tct_created_at = Column(DateTime, default=get_bogota_now)

    # Relaciones
    template = relationship("CompoundTemplate", back_populates="test_links")
    test = relationship("TestsLab", back_populates="compound_template_links")

    def __repr__(self):
        return f"<TestCompoundTemplate(tct_id={self.tct_id}, test={self.tct_test_id}, template={self.tct_template_id})>"
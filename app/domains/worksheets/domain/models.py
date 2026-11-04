from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from utils.timezone import get_bogota_now


class WorkSheet(Base):
    """Hoja de trabajo: agrupa estudios para imprimirlos juntos en Planes de Trabajo."""

    __tablename__ = "WorkSheets"

    ws_id = Column(Integer, primary_key=True, index=True)
    ws_name = Column(String(150), nullable=False)
    ws_description = Column(Text, nullable=True)
    # Sede en la que aplica (NULL = todas las sedes)
    ws_headquarter_id = Column(Integer, ForeignKey("Headquarters.id"), nullable=True)
    # Sector / área del laboratorio (Work_groups)
    ws_work_group_id = Column(Integer, ForeignKey("Work_groups.wg_id"), nullable=True)
    # Agrega una columna en blanco al imprimir, para anotaciones a mano
    ws_include_free_column = Column(Boolean, nullable=False, default=False)
    ws_active = Column(Boolean, nullable=False, default=True)
    ws_created_at = Column(DateTime, default=get_bogota_now)
    ws_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    study_links = relationship(
        "WorkSheetStudy",
        back_populates="worksheet",
        cascade="all, delete-orphan",
        order_by="WorkSheetStudy.wss_order",
    )

    def __repr__(self):
        return f"<WorkSheet(id={self.ws_id}, name='{self.ws_name}')>"


class WorkSheetStudy(Base):
    """Estudios vinculados a una hoja de trabajo, en el orden en que se imprimen."""

    __tablename__ = "WorkSheetStudies"
    __table_args__ = (UniqueConstraint("wss_worksheet_id", "wss_study_id", name="uq_worksheet_study"),)

    wss_id = Column(Integer, primary_key=True, index=True)
    wss_worksheet_id = Column(Integer, ForeignKey("WorkSheets.ws_id", ondelete="CASCADE"), nullable=False, index=True)
    wss_study_id = Column(Integer, ForeignKey("StudiesLab.id", ondelete="CASCADE"), nullable=False, index=True)
    wss_order = Column(Integer, nullable=False, default=0)

    worksheet = relationship("WorkSheet", back_populates="study_links")
    study = relationship("StudiesLab", foreign_keys=[wss_study_id], lazy="joined")

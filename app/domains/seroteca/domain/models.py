from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from utils.timezone import get_bogota_now


class SampleLog(Base):
    """Tracking event — every state change or movement of a sample tube."""

    __tablename__ = "SamplesLog"

    sl_id = Column(Integer, primary_key=True, index=True)
    log_sample_order_id = Column(Integer, ForeignKey("SamplesOrder.so_id", ondelete="CASCADE"), nullable=True)
    log_state = Column(Integer, nullable=True)
    # 0=Recibida  1=En proceso  2=Almacenada  3=Retirada  4=Descartada
    log_location_id = Column(Integer, ForeignKey("locations.loc_id", ondelete="SET NULL"), nullable=True)
    log_observation = Column(Text, nullable=True)
    log_user_id = Column(Integer, ForeignKey("AppUsers.usr_id", ondelete="SET NULL"), nullable=True)
    log_create_at = Column(DateTime, default=get_bogota_now)

    sample = relationship("SamplesOrder", foreign_keys=[log_sample_order_id])
    location = relationship("Location", foreign_keys=[log_location_id])
    user = relationship("AppUser", foreign_keys=[log_user_id])


class Seroteca(Base):
    """Physical storage unit (freezer, refrigerator, cabinet)."""

    __tablename__ = "Serotecas"

    s_id = Column(Integer, primary_key=True, index=True)
    s_name = Column(String(255), nullable=False)
    s_description = Column(Text, nullable=True)
    s_location_id = Column(Integer, ForeignKey("locations.loc_id", ondelete="SET NULL"), nullable=True)
    s_headquarter_id = Column(Integer, ForeignKey("Headquarters.id", ondelete="SET NULL"), nullable=True)
    s_active = Column(Boolean, default=True, nullable=False)
    s_created_at = Column(DateTime, default=get_bogota_now)
    s_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    location = relationship("Location", foreign_keys=[s_location_id])
    headquarter = relationship("Headquarter", foreign_keys=[s_headquarter_id])
    racks = relationship("Gradilla", back_populates="seroteca", cascade="all, delete-orphan")


class Gradilla(Base):
    """Rack (gradilla) inside a seroteca. User defines rows × cols."""

    __tablename__ = "Gradillas"

    g_id = Column(Integer, primary_key=True, index=True)
    g_name = Column(String(255), nullable=False)
    g_seroteca_id = Column(Integer, ForeignKey("Serotecas.s_id", ondelete="CASCADE"), nullable=False)
    g_rows = Column(Integer, nullable=False)
    g_cols = Column(Integer, nullable=False)
    g_active = Column(Boolean, default=True, nullable=False)
    g_created_by = Column(Integer, ForeignKey("AppUsers.usr_id", ondelete="SET NULL"), nullable=True)
    g_created_at = Column(DateTime, default=get_bogota_now)
    g_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    seroteca = relationship("Seroteca", back_populates="racks")
    positions = relationship("GradillaPosicion", back_populates="rack", cascade="all, delete-orphan")
    created_by_user = relationship("AppUser", foreign_keys=[g_created_by])


class GradillaPosicion(Base):
    """Individual position (cell) inside a rack. Auto-generated on rack creation."""

    __tablename__ = "GradillaPosiciones"

    gp_id = Column(Integer, primary_key=True, index=True)
    gp_gradilla_id = Column(Integer, ForeignKey("Gradillas.g_id", ondelete="CASCADE"), nullable=False)
    gp_row = Column(Integer, nullable=False)
    gp_col = Column(Integer, nullable=False)
    gp_sample_id = Column(Integer, ForeignKey("SamplesOrder.so_id", ondelete="SET NULL"), nullable=True)
    gp_occupied = Column(Boolean, default=False, nullable=False)
    gp_stored_at = Column(DateTime, nullable=True)
    gp_stored_by_id = Column(Integer, ForeignKey("AppUsers.usr_id", ondelete="SET NULL"), nullable=True)

    rack = relationship("Gradilla", back_populates="positions")
    sample = relationship("SamplesOrder", foreign_keys=[gp_sample_id])
    stored_by = relationship("AppUser", foreign_keys=[gp_stored_by_id])
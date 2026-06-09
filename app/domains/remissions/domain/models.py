from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from utils.timezone import get_bogota_now


class ExternalReferenceLaboratory(Base):
    """
    Directorio de laboratorios de referencia externos.
    """
    __tablename__ = "ExternalReferenceLaboratories"

    erl_id = Column(Integer, primary_key=True, index=True)
    erl_nit = Column(String(255), nullable=False)
    erl_name = Column(String(255), nullable=False)
    erl_address = Column(String(255), nullable=True)
    erl_phone = Column(String(255), nullable=True)
    erl_mail = Column(String(255), nullable=True)
    erl_active = Column(Boolean, default=True, nullable=False)
    erl_created_at = Column(DateTime, default=get_bogota_now)
    erl_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    def __repr__(self):
        return f"<ExternalReferenceLaboratory(id={self.erl_id}, name='{self.erl_name}')>"


class Remission(Base):
    """
    Cabecera logística de remisiones.
    - rem_state: 1=Pendiente, 2=Enviado, 3=Recibido Completo, 4=Recibido con Novedad, 5=Cancelado
    """
    __tablename__ = "Remissions"

    rem_id = Column(Integer, primary_key=True, index=True)
    rem_consecutive = Column(String(50), nullable=False)
    rem_type = Column(String(20), nullable=False)  # 'LOCAL' o 'EXTERNAL'
    rem_origin_headquarter_id = Column(Integer, ForeignKey("Headquarters.id"), nullable=False)
    rem_dest_headquarter_id = Column(Integer, ForeignKey("Headquarters.id"), nullable=True)
    rem_dest_external_lab_id = Column(Integer, ForeignKey("ExternalReferenceLaboratories.erl_id"), nullable=True)
    rem_state = Column(Integer, nullable=False)  # 1..5
    rem_courier_name = Column(String(255), nullable=True)
    rem_temperature_courier = Column(String(100), nullable=True)
    rem_observations = Column(Text, nullable=True)
    rem_created_by_user_id = Column(Integer, ForeignKey("AppUsers.usr_id"), nullable=False)
    rem_created_at = Column(DateTime, default=get_bogota_now, nullable=False)
    rem_sent_at = Column(DateTime, nullable=True)
    rem_received_at = Column(DateTime, nullable=True)

    # Relaciones
    origin_headquarter = relationship("Headquarter", foreign_keys=[rem_origin_headquarter_id])
    dest_headquarter = relationship("Headquarter", foreign_keys=[rem_dest_headquarter_id])
    dest_external_lab = relationship("ExternalReferenceLaboratory", foreign_keys=[rem_dest_external_lab_id])
    created_by_user = relationship("AppUser", foreign_keys=[rem_created_by_user_id])
    details = relationship("RemissionDetail", back_populates="remission", cascade="all, delete-orphan")
    state_logs = relationship("RemissionStatesLog", back_populates="remission", cascade="all, delete-orphan")

    # Check constraints (enforced at DB level via table definition; app-level validation also required)
    __table_args__ = (
        CheckConstraint(
            "rem_type IN ('LOCAL', 'EXTERNAL')",
            name="chk_remission_type",
        ),
        CheckConstraint(
            "(rem_type = 'LOCAL' AND rem_dest_headquarter_id IS NOT NULL AND rem_dest_external_lab_id IS NULL) OR "
            "(rem_type = 'EXTERNAL' AND rem_dest_external_lab_id IS NOT NULL AND rem_dest_headquarter_id IS NULL)",
            name="chk_remission_destination",
        ),
    )

    def __repr__(self):
        return f"<Remission(id={self.rem_id}, consecutive='{self.rem_consecutive}', state={self.rem_state})>"


class RemissionDetail(Base):
    """
    Detalle de ítems remitidos (muestra y examen).
    - remd_item_state: 1=Cargado, 2=Recibido Conforme, 3=Rechazado en Destino
    """
    __tablename__ = "RemissionDetails"

    remd_id = Column(Integer, primary_key=True, index=True)
    remd_remission_id = Column(Integer, ForeignKey("Remissions.rem_id", ondelete="CASCADE"), nullable=False)
    remd_sample_order_id = Column(Integer, ForeignKey("SamplesOrder.so_id"), nullable=False)
    remd_order_detail_id = Column(Integer, ForeignKey("OrdersDetails.od_id"), nullable=False)
    remd_item_state = Column(Integer, nullable=False)  # 1, 2, 3
    remd_rejection_reason = Column(Text, nullable=True)
    remd_received_by_user_id = Column(Integer, ForeignKey("AppUsers.usr_id"), nullable=True)
    remd_updated_at = Column(DateTime, default=get_bogota_now)

    # Relaciones
    remission = relationship("Remission", back_populates="details")
    sample_order = relationship("SamplesOrder", foreign_keys=[remd_sample_order_id])
    order_detail = relationship("OrdersDetail", foreign_keys=[remd_order_detail_id])
    received_by_user = relationship("AppUser", foreign_keys=[remd_received_by_user_id])

    def __repr__(self):
        return f"<RemissionDetail(id={self.remd_id}, remission_id={self.remd_remission_id}, state={self.remd_item_state})>"


class RemissionStatesLog(Base):
    """
    Historial de auditoría de cambios de estado en remisiones.
    """
    __tablename__ = "RemissionStatesLog"

    rsl_id = Column(Integer, primary_key=True, index=True)
    rsl_remission_id = Column(Integer, ForeignKey("Remissions.rem_id", ondelete="CASCADE"), nullable=False)
    rsl_state_before = Column(Integer, nullable=True)
    rsl_state_after = Column(Integer, nullable=False)
    rsl_changed_by_user_id = Column(Integer, ForeignKey("AppUsers.usr_id"), nullable=False)
    rsl_notes = Column(Text, nullable=True)
    rsl_created_at = Column(DateTime, default=get_bogota_now, nullable=False)

    # Relaciones
    remission = relationship("Remission", back_populates="state_logs")
    changed_by_user = relationship("AppUser", foreign_keys=[rsl_changed_by_user_id])

    def __repr__(self):
        return f"<RemissionStatesLog(id={self.rsl_id}, remission_id={self.rsl_remission_id}, state_before={self.rsl_state_before}, state_after={self.rsl_state_after})>"
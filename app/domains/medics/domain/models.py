from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.database import Base
from utils.timezone import get_bogota_now


class Medic(Base):
    """Médico remitente (maestro). Se asigna a la orden en Orders.o_medic_id (→ med_id)."""

    __tablename__ = "Medics"

    med_id = Column(Integer, primary_key=True, index=True)
    # Código propio del médico (lo asigna el laboratorio); único
    med_codigo = Column(String(30), nullable=False, unique=True)
    med_name = Column(String(200), nullable=False)
    med_document_number = Column(String(30), nullable=True, index=True)
    med_specialty = Column(String(150), nullable=True)  # especialidad del médico
    med_card_professional_number = Column(String(50), nullable=True)
    med_phone = Column(String(50), nullable=True)
    med_mail = Column(String(150), nullable=True)
    med_user = Column(String(100), nullable=True)
    # Hash bcrypt; nunca se devuelve en la API
    med_password = Column(String(255), nullable=True)
    med_reset_password = Column(Boolean, nullable=False, default=False)
    med_is_locked = Column(Boolean, nullable=False, default=False)
    med_is_active = Column(Boolean, nullable=False, default=True)
    med_created_at = Column(DateTime, default=get_bogota_now)
    med_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    def __repr__(self):
        return f"<Medic(id={self.med_id}, codigo='{self.med_codigo}', name='{self.med_name}')>"

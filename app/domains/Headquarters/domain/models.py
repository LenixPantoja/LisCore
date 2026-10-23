from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.core.database import Base
from datetime import datetime
from utils.timezone import get_bogota_now

class Headquarter(Base):
    __tablename__ = "Headquarters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    resolution = Column(String(255), nullable=True)
    prefix = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)
    phone = Column(String(255), nullable=True)
    City = Column(Integer, nullable=True)  # Mapeado a la tabla Cities
    active = Column(Boolean, default=True)
    # Próximo consecutivo de órdenes de la sede (1..999999999), ver utils/Consecutives/consecutive_headquarters.py
    order_consecutive_next = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime, default=get_bogota_now)
    updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    def __repr__(self):
        return f"<Headquarter(id={self.id}, name='{self.name}')>"
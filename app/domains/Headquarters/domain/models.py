from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.core.database import Base
from datetime import datetime

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Headquarter(id={self.id}, name='{self.name}')>"
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base
from utils.timezone import get_bogota_now


class Barcode(Base):
    __tablename__ = "barcodes"

    id = Column(Integer, primary_key=True, index=True)
    label_type = Column(String(20), nullable=False, index=True)
    barcode = Column(Text, nullable=False)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=get_bogota_now)
    updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    def __repr__(self):
        return f"<Barcode(id={self.id}, label_type='{self.label_type}', is_active={self.is_active})>"

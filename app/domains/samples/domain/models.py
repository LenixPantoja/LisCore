from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from utils.timezone import get_bogota_now

class SampleType(Base):
    __tablename__ = "SampleTypes"

    st_id = Column(Integer, primary_key=True, index=True)
    st_name = Column(String(255))
    st_color = Column(String(255))
    st_sufix = Column(Integer)
    st_type_temp = Column(String(255))
    st_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<SampleType(id={self.st_id}, name='{self.st_name}')>"

class SamplesOrder(Base):
    __tablename__ = "SamplesOrder"

    so_id = Column(Integer, primary_key=True, index=True)
    so_order_id = Column(Integer, ForeignKey("Orders.o_id"))
    so_sample_type_id = Column(Integer, ForeignKey("SampleTypes.st_id"))
    so_barcode = Column(String(255), unique=True, index=True)
    so_state = Column(Integer)
    so_number_studies = Column(Integer)
    so_current_location_id = Column(Integer)
    so_created_at = Column(DateTime, default=get_bogota_now)
    so_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    # Relaciones
    order = relationship("Order", foreign_keys=[so_order_id])
    sample_type = relationship("SampleType")

    def __repr__(self):
        return f"<SamplesOrder(id={self.so_id}, barcode='{self.so_barcode}')>"
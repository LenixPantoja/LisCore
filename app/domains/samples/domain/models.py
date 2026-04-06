from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

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
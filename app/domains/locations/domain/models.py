from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

class Location(Base):
    __tablename__ = "locations"

    loc_id = Column(Integer, primary_key=True, index=True)
    loc_name = Column(String(500))
    loc_active = Column(Boolean, default=True)

from sqlalchemy import Column, Integer, Text, DateTime
from app.core.database import Base
from utils.timezone import get_bogota_now


class AppTrace(Base):
    __tablename__ = "AppTrace"

    id = Column(Integer, primary_key=True, index=True)
    usr_id = Column(Integer, nullable=True)
    order_id = Column(Integer, nullable=True)
    operation_type = Column(Integer, nullable=True)
    operation_description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    test_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=get_bogota_now)

    def __repr__(self):
        return f"<AppTrace(id={self.id}, operation_type={self.operation_type}, usr_id={self.usr_id})>"

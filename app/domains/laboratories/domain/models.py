from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Laboratory(Base):
    __tablename__ = "Laboratories"

    l_id = Column(Integer, primary_key=True, index=True)
    l_order_detail_id = Column(Integer, ForeignKey("OrdersDetails.od_id"), unique=True)
    l_test_id = Column(Integer, ForeignKey("TestsLab.id"))
    l_result = Column(String(255), nullable=True)
    l_result_num = Column(Numeric, nullable=True)
    l_result_comp = Column(Text, nullable=True)
    l_result_graphic = Column(Text, nullable=True)
    l_nota_validation = Column(String(255), nullable=True)
    l_state = Column(Integer, default=0)
    l_date_transmited = Column(DateTime, nullable=True)
    l_date_validatie = Column(DateTime, nullable=True)
    l_user_validation_id = Column(Integer, nullable=True)
    a_analyzer_result_id = Column(Integer, nullable=True)
    l_created_at = Column(DateTime, default=datetime.utcnow)
    l_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    order_detail = relationship("app.domains.orders.domain.models.OrdersDetail")
    test = relationship("app.domains.testslabs.domain.models.TestsLab")

    def __repr__(self):
        return f"<Laboratory(id={self.l_id}, order_detail_id={self.l_order_detail_id}, result='{self.l_result}')>"
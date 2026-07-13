from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from utils.timezone import get_bogota_now

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
    l_user_validation_id = Column(Integer, ForeignKey("AppUsers.usr_id"), nullable=True)
    a_analyzer_result_id = Column(Integer, nullable=True)
    l_created_at = Column(DateTime, default=get_bogota_now)
    l_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    # Relaciones
    order_detail = relationship("OrdersDetail", foreign_keys=[l_order_detail_id])
    test = relationship("TestsLab", foreign_keys=[l_test_id])
    user_validation = relationship("AppUser", foreign_keys=[l_user_validation_id])
    preliminaries = relationship("LaboratoryPreliminary", back_populates="laboratory", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Laboratory(id={self.l_id}, order_detail_id={self.l_order_detail_id}, result='{self.l_result}')>"


class LaboratoryPreliminary(Base):
    """
    Almacena resultados preliminares para un laboratorio (ej. microbiología).
    Cada registro representa un resultado parcial en una secuencia, registrado
    por un analizador en una fecha/hora determinada.

    Estados (lp_state):
        0 - Pendiente
        1 - Validado
        2 - Desvalidado
    """
    __tablename__ = "LaboratoryPreliminaries"

    lp_id = Column(Integer, primary_key=True, index=True)
    lp_laboratory_id = Column(Integer, ForeignKey("Laboratories.l_id"), nullable=False)
    lp_secuence = Column(Integer, nullable=False)
    lp_result = Column(Text, nullable=True)
    lp_date_preliminary = Column(DateTime, nullable=True)
    analyzer = Column(String(255), nullable=True)
    lp_state = Column(Integer, default=0, nullable=False)

    # Relaciones
    laboratory = relationship("Laboratory", back_populates="preliminaries")

    def __repr__(self):
        return f"<LaboratoryPreliminary(id={self.lp_id}, lab_id={self.lp_laboratory_id}, seq={self.lp_secuence}, state={self.lp_state})>"

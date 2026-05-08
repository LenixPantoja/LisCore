from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from utils.timezone import get_bogota_now

class Order(Base):
    __tablename__ = "Orders"

    o_id = Column(Integer, primary_key=True, index=True)
    o_number = Column(String(255), index=True)
    o_date = Column(Date)
    o_his_id = Column(Integer, ForeignKey("Patients.pt_id"), nullable=False)
    o_print_date = Column(DateTime, nullable=True)
    o_age = Column(String(255))
    o_pregnated = Column(Boolean, default=False)
    o_week_pregnated = Column(String(255), nullable=True)
    o_priority = Column(Integer, default=0)
    o_mail_sent = Column(Integer, default=0)
    o_whatsapp_sent = Column(Integer, default=0)
    o_autorizacion = Column(String(255), nullable=True)
    o_service_id = Column(Integer, ForeignKey("Services.id"), nullable=True)
    o_diagnoses_id = Column(Integer, ForeignKey("Diagnoses.diag_id"), nullable=True)
    o_headquarter_id = Column(Integer, nullable=True) # Falta FK formal si no existe tabla headquarters mapeada
    o_AppUser_id = Column(Integer, nullable=True) # Corresponde a Users
    o_enterprise_id = Column(Integer, ForeignKey("Enterprises.en_id"), nullable=True)
    o_scholarity = Column(Integer, ForeignKey("Schooling.id"), nullable=True)
    o_order_state = Column(Integer, default=1)
    o_pat_num_whatsapp = Column(String(255), nullable=True)
    o_pat_mail = Column(String(255), nullable=True)
    o_note = Column(Text, nullable=True)
    o_created_at = Column(DateTime, default=get_bogota_now)
    o_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)
    o_tariff_id = Column(Integer, ForeignKey("Tariffs.t_id"), nullable=True)

    # Relaciones
    patient = relationship("Patient", foreign_keys=[o_his_id])
    service = relationship("Service", foreign_keys=[o_service_id])
    diagnosis = relationship("Diagnosis", foreign_keys=[o_diagnoses_id])
    enterprise = relationship("Enterprise", foreign_keys=[o_enterprise_id])
    schooling = relationship("Schooling", foreign_keys=[o_scholarity])
    tariff = relationship("Tariff", foreign_keys=[o_tariff_id])
    details = relationship("OrdersDetail", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.o_id}, number='{self.o_number}')>"

class OrdersDetail(Base):
    __tablename__ = "OrdersDetails"

    od_id = Column(Integer, primary_key=True, index=True)
    od_order_id = Column(Integer, ForeignKey("Orders.o_id"))
    od_study_id = Column(Integer, ForeignKey("StudiesLab.id"))
    od_state = Column(Integer)
    od_print_date = Column(DateTime, nullable=True)
    o_checking_date = Column(DateTime, nullable=True)
    od_created_at = Column(DateTime, default=get_bogota_now)
    od_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    # Relaciones
    order = relationship("Order", back_populates="details")
    study = relationship("StudiesLab", foreign_keys=[od_study_id])

    def __repr__(self):
        return f"<OrdersDetail(id={self.od_id}, order_id={self.od_order_id}, study_id={self.od_study_id})>"
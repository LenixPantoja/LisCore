from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class InboundOrder(Base):
    __tablename__ = "InboundOrders"

    io_id = Column(Integer, primary_key=True, index=True)
    io_number_request = Column(String(500))
    io_date_request = Column(DateTime, nullable=True)
    io_date_transmission = Column(DateTime, nullable=True)
    io_patient_id = Column(Integer, ForeignKey("Patients.pt_id"), nullable=True)
    io_tariff_id = Column(Integer, ForeignKey("Tariffs.t_id"), nullable=True)
    io_service_id = Column(Integer, ForeignKey("Services.id"), nullable=True)
    io_diagnostic_id = Column(Integer, ForeignKey("Diagnoses.diag_id"), nullable=True)
    io_origin = Column(String(500))
    io_priority = Column(Integer, nullable=True)
    io_medic_document_number = Column(String(500))
    io_medic_name = Column(String(500))
    io_headquarter_id = Column(Integer, nullable=True)
    io_country_id = Column(Integer, ForeignKey("Countries.id"), nullable=True)
    io_enterprise_id = Column(Integer, ForeignKey("Enterprises.en_id"), nullable=True)
    io_municipality_id = Column(Integer, nullable=True)
    io_scholarity_id = Column(Integer, ForeignKey("Schooling.id"), nullable=True)
    io_created_at = Column(DateTime, nullable=True)
    io_updated_at = Column(DateTime, nullable=True)

    # Relationships
    patient = relationship("app.domains.patients.domain.models.Patient")
    tariff = relationship("app.domains.contractstariffs.domain.models.Tariff")
    service = relationship("app.domains.masters.domain.models.Service")
    diagnosis = relationship("app.domains.masters.domain.models.Diagnosis")
    country = relationship("app.domains.masters.domain.models.Country")
    enterprise = relationship("app.domains.enterprises.domain.models.Enterprise")
    scholarity = relationship("app.domains.masters.domain.models.Schooling")

    details = relationship("InboundOrderDetail", back_populates="inbound_order", cascade="all, delete-orphan")


class InboundOrderDetail(Base):
    __tablename__ = "InboundOrdersDetails"

    iod_id = Column(Integer, primary_key=True, index=True)
    iod_inboundOrder_id = Column(Integer, ForeignKey("InboundOrders.io_id"), unique=True)
    iod_study_id = Column(Integer, ForeignKey("StudiesLab.id"), nullable=True)
    iod_state = Column(Integer, nullable=True)
    iod_observation = Column(Text, nullable=True)
    iod_laboratory_id = Column(Integer, nullable=True)
    iod_order_id = Column(Integer, ForeignKey("Orders.o_id"), nullable=True)
    iod_study_consecutive = Column(String(500))
    iod_created_at = Column(DateTime, nullable=True)
    iod_updated_at = Column(DateTime, nullable=True)

    # Relationships
    inbound_order = relationship("InboundOrder", back_populates="details")
    study = relationship("app.domains.studieslab.domain.models.StudiesLab")
    order = relationship("app.domains.orders.domain.models.Order")

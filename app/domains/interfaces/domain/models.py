from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class InterfacesRest(Base):
    __tablename__ = "InterfacesRest"

    it_id = Column(Integer, primary_key=True, index=True)
    it_enterprise_id = Column(Integer, ForeignKey("Enterprises.en_id"), nullable=True)
    it_tariff_id = Column(Integer, ForeignKey("Tariffs.t_id"), nullable=True)
    it_state = Column(Boolean, default=True)
    it_created_at = Column(DateTime, nullable=True)
    it_updated_at = Column(DateTime, nullable=True)

    enterprise = relationship("app.domains.enterprises.domain.models.Enterprise")
    tariff = relationship("app.domains.contractstariffs.domain.models.Tariff")
    details = relationship("InterfacesRestDetail", back_populates="interface_rest", cascade="all, delete-orphan")


class InterfacesRestDetail(Base):
    __tablename__ = "InterfacesRestDetail"

    itd_id = Column(Integer, primary_key=True, index=True)
    itd_interface_rest_id = Column(Integer, ForeignKey("InterfacesRest.it_id"))
    itd_study_id = Column(Integer, ForeignKey("StudiesLab.id"), nullable=True)
    itd_send_code = Column(String(500))
    itd_receipt_code = Column(String(500))
    itd_created_at = Column(DateTime, nullable=True)
    itd_updated_at = Column(DateTime, nullable=True)

    interface_rest = relationship("InterfacesRest", back_populates="details")
    study = relationship("app.domains.studieslab.domain.models.StudiesLab")

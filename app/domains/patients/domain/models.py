from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Patient(Base):
    __tablename__ = "Patients"

    pt_id = Column(Integer, primary_key=True, index=True)
    pt_Number_document = Column(String(255), index=True)
    pt_firts_name = Column(String(255))
    pt_middle_name = Column(String(255), nullable=True)
    pt_last_name = Column(String(255))
    pt_second_last_name = Column(String(255), nullable=False)
    pt_sex_type = Column(Integer, ForeignKey("Sex_Types.id"), nullable=True)
    pt_phone_number = Column(String(255), nullable=True)
    pt_mail = Column(String(255), nullable=True)
    pt_address = Column(String(255), nullable=True)
    pt_date_of_birth = Column(Date, nullable=True)
    pt_authorize_habeas_data = Column(Boolean, default=False)
    pt_afiliation_type = Column(Integer, ForeignKey("Afiliation_type.id"), nullable=True)
    pt_enterprise_id = Column(Integer, ForeignKey("Enterprises.en_id"), nullable=True)
    pt_Document_Type_id = Column(Integer, ForeignKey("DocumentsTypes.dt_id"), nullable=True)
    pt_city_id = Column(Integer, ForeignKey("Cities.id"), nullable=True)
    pt_password = Column(String(500), nullable=True)
    pt_created_at = Column(DateTime, default=datetime.utcnow)
    pt_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    sex_type = relationship("app.domains.masters.domain.models.SexType")
    afiliation = relationship("app.domains.masters.domain.models.AfiliationType")
    enterprise = relationship("app.domains.enterprises.domain.models.Enterprise")
    document_type = relationship("app.domains.masters.domain.models.DocumentType")
    city = relationship("app.domains.masters.domain.models.City")

    def __repr__(self):
        return f"<Patient(id={self.pt_id}, name='{self.pt_firts_name} {self.pt_last_name}')>"
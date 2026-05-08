from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from utils.timezone import get_bogota_now

class Patient(Base):
    __tablename__ = "Patients"

    pt_id = Column(Integer, primary_key=True, index=True)
    pt_Number_document = Column(String(255), unique=True, index=True)
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
    pt_created_at = Column(DateTime, default=get_bogota_now)
    pt_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    # Relaciones
    sex_type = relationship("SexType", foreign_keys=[pt_sex_type])
    afiliation = relationship("AfiliationType", foreign_keys=[pt_afiliation_type])
    enterprise = relationship("Enterprise", foreign_keys=[pt_enterprise_id])
    document_type = relationship("DocumentType", foreign_keys=[pt_Document_Type_id])
    city = relationship("City", foreign_keys=[pt_city_id])

    def __repr__(self):
        return f"<Patient(id={self.pt_id}, name='{self.pt_firts_name} {self.pt_last_name}')>"
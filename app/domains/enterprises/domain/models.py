from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from utils.timezone import get_bogota_now

class Enterprise(Base):
    __tablename__ = "Enterprises"

    en_id = Column(Integer, primary_key=True, index=True)
    en_code = Column(String(255), unique=True, index=True)
    en_name = Column(String(255), index=True)
    en_description = Column(String(255), nullable=True)
    en_nit = Column(String(255), unique=True, index=True)
    en_div = Column(String(255), nullable=True)
    en_address = Column(String(255), nullable=True)
    en_phone = Column(String(255), nullable=True)
    en_Legal_representative = Column(String(255), nullable=True)
    en_mail = Column(String(255), unique=True, index=True, nullable=True)
    en_observations = Column(String(255), nullable=True)
    en_active = Column(Boolean, default=True)
    en_send_mail = Column(Boolean, default=False)
    en_send_whatsapp = Column(Boolean, default=False)
    en_alternative_contact = Column(String(255), nullable=True)
    en_email_electronic_invoice = Column(String(255), nullable=True)
    en_regimen_id = Column(Integer, nullable=True)
    en_classification_id = Column(Integer, nullable=True)
    en_document_type_id = Column(Integer, nullable=True)
    en_city_id = Column(Integer, nullable=True)
    en_liability_type_id = Column(Integer, nullable=True)
    en_type_organization_id = Column(Integer, nullable=True)
    en_created_at = Column(DateTime, default=get_bogota_now)
    en_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)
    en_password = Column(String(500), nullable=True) # This field is unusual for an enterprise, but included as per SQL schema

    def __repr__(self):
        return f"<Enterprise(id={self.en_id}, name='{self.en_name}', nit='{self.en_nit}')>"
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Numeric, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from utils.timezone import get_bogota_now


class Invoice(Base):
    __tablename__ = "Invoices"

    inv_id = Column(Integer, primary_key=True, index=True)
    inv_number = Column(String(255), index=True, nullable=True)
    inv_date = Column(Date, nullable=True)
    inv_due_date = Column(Date, nullable=True)
    inv_enterprise_id = Column(Integer, ForeignKey("Enterprises.en_id"), nullable=True)
    inv_patient_id = Column(Integer, ForeignKey("Patients.pt_id"), nullable=True)
    inv_contract_id = Column(Integer, ForeignKey("ContractsTariffs.ct_id"), nullable=True)
    inv_subtotal = Column(Numeric, nullable=True)
    inv_tax = Column(Numeric, nullable=True)
    inv_total = Column(Numeric, nullable=True)
    inv_state = Column(Integer, nullable=True)
    inv_type = Column(Integer, nullable=True)
    inv_sub_type_invoice = Column(Integer, nullable=True)
    inv_notes = Column(Text, nullable=True)
    inv_created_by = Column(Integer, ForeignKey("AppUsers.usr_id"), nullable=True)
    inv_created_at = Column(Date, default=get_bogota_now)
    inv_updated_at = Column(Date, default=get_bogota_now, onupdate=get_bogota_now)
    tariff_id = Column(BigInteger, nullable=True)

    # Relaciones
    enterprise = relationship("Enterprise", foreign_keys=[inv_enterprise_id])
    patient = relationship("Patient", foreign_keys=[inv_patient_id])
    contract = relationship("ContractTariff", foreign_keys=[inv_contract_id])
    created_by = relationship("AppUser", foreign_keys=[inv_created_by])
    details = relationship("InvoiceDetail", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Invoice(id={self.inv_id}, number='{self.inv_number}')>"


class InvoiceDetail(Base):
    __tablename__ = "InvoicesDetail"

    invd_id = Column(Integer, primary_key=True, index=True)
    invd_invoice_id = Column(Integer, ForeignKey("Invoices.inv_id"), nullable=True)
    invd_order_detail_id = Column(Integer, ForeignKey("OrdersDetails.od_id"), nullable=True)
    invd_study_id = Column(Integer, ForeignKey("StudiesLab.id"), nullable=True)
    invd_value = Column(Numeric, nullable=True)
    invd_discount = Column(Numeric, nullable=True)
    invd_total = Column(Numeric, nullable=True)
    invd_created_by = Column(Integer, ForeignKey("AppUsers.usr_id"), nullable=True)
    invd_created_at = Column(DateTime, default=get_bogota_now)
    invd_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    # Relaciones
    invoice = relationship("Invoice", back_populates="details")
    order_detail = relationship("OrdersDetail", foreign_keys=[invd_order_detail_id])
    study = relationship("StudiesLab", foreign_keys=[invd_study_id])
    created_by = relationship("AppUser", foreign_keys=[invd_created_by])

    def __repr__(self):
        return f"<InvoiceDetail(id={self.invd_id}, invoice_id={self.invd_invoice_id})>"

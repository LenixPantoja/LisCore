from sqlalchemy import Column, Integer, String, Boolean, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import date
from app.core.database import Base

class Tariff(Base):
    __tablename__ = "Tariffs"

    t_id = Column(Integer, primary_key=True, index=True)
    t_name = Column(String(255))
    t_description = Column(String(255))
    t_activo = Column(Boolean, default=True)
    t_created_at = Column(Date, default=date.today)
    t_update_at = Column(Date, default=date.today, onupdate=date.today)

    details = relationship("TariffDetail", back_populates="tariff", cascade="all, delete-orphan")
    contracts_link = relationship("ContractTariff", back_populates="tariff")

class TariffDetail(Base):
    __tablename__ = "TariffsDetail"

    td_id = Column(Integer, primary_key=True, index=True)
    td_tariff_id = Column(Integer, ForeignKey("Tariffs.t_id"))
    td_studie_id = Column(Integer, ForeignKey("StudiesLab.id"))
    td_value = Column(Numeric)

    tariff = relationship("Tariff", back_populates="details")
    studie = relationship("StudiesLab")

class Contract(Base):
    __tablename__ = "Contracts"

    co_id = Column(Integer, primary_key=True, index=True)
    co_code = Column(String(255), nullable=True)
    co_observations = Column(String(255), nullable=True)
    co_value_contracted = Column(Numeric, nullable=True)
    co_value_consumed = Column(Numeric, nullable=True)
    co_value_alarm = Column(Numeric, nullable=True)
    co_billing_type = Column(Integer, nullable=True)
    co_contract_number = Column(String(255), nullable=True)
    co_number_poliza = Column(String(255), nullable=True)
    co_active = Column(Boolean, default=True, nullable=True)
    co_created_at = Column(Date, nullable=True)
    co_updated_at = Column(Date, nullable=True)
    co_enterprise_id = Column(Integer, ForeignKey("Enterprises.en_id"), nullable=True)

    tariffs_link = relationship("ContractTariff", back_populates="contract")
    enterprise = relationship("Enterprise", backref="contracts")

class ContractTariff(Base):
    __tablename__ = "ContractsTariffs"
    __table_args__ = (
        UniqueConstraint('ct_contract_id', 'ct_tariff_id', name='uq_contract_tariff'),
    )

    ct_id = Column(Integer, primary_key=True, index=True)
    ct_contract_id = Column(Integer, ForeignKey("Contracts.co_id"))
    ct_tariff_id = Column(Integer, ForeignKey("Tariffs.t_id"))
    ct_active = Column(Boolean, default=True)
    ct_start_date = Column(Date)
    ct_end_date = Column(Date)

    contract = relationship("Contract", back_populates="tariffs_link")
    tariff = relationship("Tariff", back_populates="contracts_link")
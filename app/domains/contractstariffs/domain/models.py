from sqlalchemy import Column, Integer, String, Boolean, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Tariff(Base):
    __tablename__ = "Tariffs"

    t_id = Column(Integer, primary_key=True, index=True)
    t_name = Column(String(255))
    t_description = Column(String(255))
    t_activo = Column(Boolean, default=True)
    t_created_at = Column(Date)
    t_update_at = Column(Date)

    details = relationship("TariffDetail", back_populates="tariff", cascade="all, delete-orphan")
    contracts_link = relationship("ContractTariff", back_populates="tariff")

class TariffDetail(Base):
    __tablename__ = "TariffsDetail"

    td_id = Column(Integer, primary_key=True, index=True)
    td_tariff_id = Column(Integer, ForeignKey("Tariffs.t_id"))
    td_studie_id = Column(Integer, ForeignKey("StudiesLab.id"))
    td_value = Column(Numeric)

    tariff = relationship("Tariff", back_populates="details")

class Contract(Base):
    __tablename__ = "Contracts"

    co_id = Column(Integer, primary_key=True, index=True)
    co_code = Column(String(255))
    co_observations = Column(String(255))
    co_value_contracted = Column(Numeric)
    co_value_consumed = Column(Numeric)
    co_value_alarm = Column(Numeric)
    co_billing_type = Column(Integer)
    co_contract_number = Column(String(255))
    co_number_poliza = Column(String(255))
    co_active = Column(Boolean, default=True)
    co_created_at = Column(Date)
    co_updated_at = Column(Date)
    co_enterprise_id = Column(Integer)

    tariffs_link = relationship("ContractTariff", back_populates="contract")

class ContractTariff(Base):
    __tablename__ = "ContractsTariffs"

    ct_id = Column(Integer, primary_key=True, index=True)
    ct_contract_id = Column(Integer, ForeignKey("Contracts.co_id"))
    ct_tariff_id = Column(Integer, ForeignKey("Tariffs.t_id"))
    ct_active = Column(Boolean, default=True)
    ct_start_date = Column(Date)
    ct_end_date = Column(Date)

    contract = relationship("Contract", back_populates="tariffs_link")
    tariff = relationship("Tariff", back_populates="contracts_link")
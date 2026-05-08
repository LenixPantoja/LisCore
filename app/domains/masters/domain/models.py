from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Country(Base):
    __tablename__ = "Countries"

    id = Column(Integer, primary_key=True, index=True)
    code_country = Column(String(255), unique=True, index=True, nullable=False)
    name_country = Column(String(255), index=True, nullable=False)
    country_active = Column(Boolean, default=True, nullable=False)

    departments = relationship("Department", back_populates="country")

    def __repr__(self):
        return f"<Country(id={self.id}, name='{self.name_country}')>"

class Department(Base):
    __tablename__ = "Departments"

    d_id = Column(Integer, primary_key=True, index=True)
    d_country_id = Column(Integer, ForeignKey("Countries.id"), nullable=False)
    d_code = Column(String(255), unique=True, index=True, nullable=False)
    d_name_department = Column(String(255), index=True, nullable=False)

    country = relationship("Country", back_populates="departments")
    cities = relationship("City", back_populates="department")

    def __repr__(self):
        return f"<Department(id={self.d_id}, name='{self.d_name_department}')>"

class City(Base):
    __tablename__ = "Cities"

    id = Column(Integer, primary_key=True, index=True)
    Department_id = Column(Integer, ForeignKey("Departments.d_id"), nullable=False)
    city_code = Column(String(255), unique=True, index=True, nullable=False)
    city_name = Column(String(255), index=True, nullable=False)
    postal_code = Column(String(255), nullable=True)

    department = relationship("Department", back_populates="cities")

    def __repr__(self):
        return f"<City(id={self.id}, name='{self.city_name}')>"

class DocumentType(Base):
    __tablename__ = "DocumentsTypes"

    dt_id = Column(Integer, primary_key=True, index=True)
    dt_code = Column(String(255))
    dt_name = Column(String(255))
    dt_id_dinamica = Column(Integer, nullable=True)

class SexType(Base):
    __tablename__ = "Sex_Types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(255))
    name = Column(String(255))
    description = Column(String(255))

class AfiliationType(Base):
    __tablename__ = "Afiliation_type"

    id = Column(Integer, primary_key=True, index=True)
    af_name = Column(String(255))

class Regime(Base):
    __tablename__ = "Regimes"

    re_id = Column(Integer, primary_key=True, index=True)
    re_name = Column(String(255))
    re_dian_code = Column(Integer)

class Service(Base):
    __tablename__ = "Services"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(255))
    name = Column(String(255))
    active = Column(Boolean, default=True)

class TypeLiability(Base):
    __tablename__ = "Type_liability"

    id = Column(Integer, primary_key=True, index=True)
    dian_code_liability = Column(String(255))
    name = Column(String(255))

    def __repr__(self):
        return f"<TypeLiability(id={self.id}, name='{self.name}')>"

class Classification(Base):
    __tablename__ = "Classifications"

    cl_id = Column(Integer, primary_key=True, index=True)
    cl_code = Column(String(255))
    cl_name = Column(String(255))

    def __repr__(self):
        return f"<Classification(id={self.cl_id}, name='{self.cl_name}')>"

class Technique(Base):
    __tablename__ = "Techniques"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    created_at = Column(Date)
    updated_at = Column(Date)

class WorkGroup(Base):
    __tablename__ = "Work_groups"

    wg_id = Column(Integer, primary_key=True, index=True)
    wg_code = Column(String(255))
    wg_name = Column(String(255))
    wg_order_of_print = Column(Integer)

class ReferralLocation(Base):
    __tablename__ = "Referral_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    description = Column(String(255))
    active = Column(Boolean, default=True)
    created_at = Column(Date)
    update_at = Column(Date)

class Diagnosis(Base):
    __tablename__ = "Diagnoses"

    diag_id = Column(Integer, primary_key=True, index=True)
    diag_code = Column(String(255))
    d_description = Column(Text)
    diag_created_at = Column(DateTime)
    diag_updated_at = Column(DateTime)

class Schooling(Base):
    __tablename__ = "Schooling"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(255))
    description = Column(String(255))
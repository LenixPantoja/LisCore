from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class StudiesLab(Base):
    __tablename__ = "StudiesLab"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(255))
    cups_code = Column(String(500))
    name = Column(String(255))
    order_of_print = Column(Integer)
    referral_location_id = Column(Integer, ForeignKey("Referral_locations.id"), nullable=True)
    work_groups_id = Column(Integer, ForeignKey("Work_groups.wg_id"), nullable=True)
    active = Column(Boolean, default=True)

    # Relaciones con Masters utilizando los modelos definidos anteriormente
    referral_location = relationship("app.domains.masters.domain.models.ReferralLocation")
    work_group = relationship("app.domains.masters.domain.models.WorkGroup")
    
    # Relación uno a muchos con el detalle de exámenes
    test_details = relationship("StudiesTestDetail", back_populates="study", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StudiesLab(id={self.id}, name='{self.name}', code='{self.code}')>"

class StudiesTestDetail(Base):
    __tablename__ = "StudiesTestDetail"

    id = Column(Integer, primary_key=True, index=True)
    studies_id = Column(Integer, ForeignKey("StudiesLab.id"))
    tests_id = Column(Integer, ForeignKey("TestsLab.id"))
    work_group_id = Column(Integer, ForeignKey("Work_groups.wg_id"))
    order_print = Column(Integer)
    is_required = Column(Boolean, default=False)

    # Relaciones
    study = relationship("StudiesLab", back_populates="test_details")
    test = relationship("app.domains.testslabs.domain.models.TestsLab")
    work_group = relationship("app.domains.masters.domain.models.WorkGroup")

    def __repr__(self):
        return f"<StudiesTestDetail(id={self.id}, study_id={self.studies_id}, test_id={self.tests_id})>"
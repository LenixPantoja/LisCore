from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class TestsLab(Base):
    __tablename__ = "TestsLab"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(500), index=True)
    name = Column(Text)
    name_abbreviation = Column(Text, nullable=True)
    
    # Relaciones con Masters y Samples
    technical_id = Column(Integer, ForeignKey("Techniques.id"), nullable=True)
    work_group_id = Column(Integer, ForeignKey("Work_groups.wg_id"), nullable=True)
    samples_type_id = Column(Integer, ForeignKey("SampleTypes.st_id"), nullable=True)
    
    units = Column(String(255), nullable=True)
    format_for_complete = Column(Text, nullable=True)
    
    alarm_value_min = Column(Numeric, nullable=True)
    alarm_value_max = Column(Numeric, nullable=True)
    female_value_min = Column(Numeric, nullable=True)
    female_value_max = Column(Numeric, nullable=True)
    male_value_min = Column(Numeric, nullable=True)
    male_value_max = Column(Numeric, nullable=True)
    boys_value_min = Column(Numeric, nullable=True)
    boys_value_max = Column(Numeric, nullable=True)
    
    active = Column(Boolean, default=True)
    test_type = Column(String(255), nullable=True)
    is_confidential = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Definición de relaciones ORM
    technique = relationship("app.domains.masters.domain.models.Technique")
    work_group = relationship("app.domains.masters.domain.models.WorkGroup")
    sample_type = relationship("app.domains.samples.domain.models.SampleType")

    def __repr__(self):
        return f"<TestsLab(id={self.id}, name='{self.name}')>"
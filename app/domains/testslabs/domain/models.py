from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from utils.timezone import get_bogota_now

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
    
    alternative_range_value = Column(Text, nullable=True)

    active = Column(Boolean, default=True)
    test_type = Column(String(255), nullable=True)
    is_confidential = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_bogota_now)
    updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    # Definición de relaciones ORM
    technique = relationship("Technique", foreign_keys=[technical_id])
    work_group = relationship("WorkGroup", foreign_keys=[work_group_id])
    sample_type = relationship("SampleType", foreign_keys=[samples_type_id])

    def __repr__(self):
        return f"<TestsLab(id={self.id}, name='{self.name}')>"
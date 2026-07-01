from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from utils.timezone import get_bogota_now


class TestsLab(Base):
    __tablename__ = "TestsLab"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(500), index=True)
    name = Column(Text)
    name_abbreviation = Column(Text, nullable=True)

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
    num_decimal_result = Column(Integer, nullable=True)
    is_formula = Column(Boolean, default=False)
    formula = Column(String(500), nullable=True)
    is_confidential = Column(Boolean, default=False)
    print_barcode = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_bogota_now)
    updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    technique = relationship("Technique", foreign_keys=[technical_id])
    work_group = relationship("WorkGroup", foreign_keys=[work_group_id])
    sample_type = relationship("SampleType", foreign_keys=[samples_type_id])
    ranges_references = relationship("RangeReference", back_populates="test", cascade="all, delete-orphan")

    formats = relationship(
        "TestslabFormatComplete",
        back_populates="testslab",
        cascade="all, delete-orphan",
    )

    compound_template_links = relationship(
        "TestCompoundTemplate",
        back_populates="test",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<TestsLab(id={self.id}, name='{self.name}')>"


class FormatComplete(Base):
    __tablename__ = "FormatComplete"

    fc_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    fc_name = Column(String(200), nullable=False)
    fc_description = Column(Text, nullable=True)
    fc_active = Column(Boolean, nullable=False, default=True)
    fc_created_at = Column(DateTime, default=get_bogota_now)
    fc_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    testslabs = relationship("TestslabFormatComplete", back_populates="format_complete")

    def __repr__(self):
        return f"<FormatComplete(id={self.fc_id}, name='{self.fc_name}')>"


class TestslabFormatComplete(Base):
    __tablename__ = "TestslabFormatComplete"

    tfc_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    tfc_testslab_id = Column(Integer, ForeignKey("TestsLab.id", ondelete="CASCADE"), nullable=False)
    tfc_format_complete_id = Column(Integer, ForeignKey("FormatComplete.fc_id", ondelete="CASCADE"), nullable=False)
    tfc_is_default = Column(Boolean, nullable=False, default=False)
    tfc_order_index = Column(Integer, nullable=False, default=0)
    tfc_created_at = Column(DateTime, default=get_bogota_now)

    testslab = relationship("TestsLab", back_populates="formats")
    format_complete = relationship("FormatComplete", back_populates="testslabs")

    def __repr__(self):
        return f"<TestslabFormatComplete(testslab={self.tfc_testslab_id}, format={self.tfc_format_complete_id})>"


class RangeReference(Base):
    __tablename__ = "RangesReferences"

    id = Column(Integer, primary_key=True, index=True)
    range_type = Column(String(50), nullable=True)
    test_id = Column(Integer, ForeignKey("TestsLab.id"), nullable=True)
    gender = Column(String(10), nullable=True)
    age_type = Column(String(10), nullable=True)
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=get_bogota_now)
    updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    test = relationship("TestsLab", back_populates="ranges_references")
    reference_values = relationship("ReferenceValue", back_populates="range_reference", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RangeReference(id={self.id}, test_id={self.test_id}, range_type='{self.range_type}')>"


class ReferenceValue(Base):
    __tablename__ = "ReferencesValues"

    id = Column(Integer, primary_key=True, index=True)
    ranges_references_id = Column(Integer, ForeignKey("RangesReferences.id"), nullable=True)
    min_value = Column(Numeric, nullable=True)
    max_values = Column(Numeric, nullable=True)
    text_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_bogota_now)
    updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    range_reference = relationship("RangeReference", back_populates="reference_values")

    def __repr__(self):
        return f"<ReferenceValue(id={self.id}, ranges_references_id={self.ranges_references_id})>"
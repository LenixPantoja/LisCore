from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from utils.timezone import get_bogota_now


class AnnexedResult(Base):
    """
    Almacena archivos PDF anexos a los resultados de una orden.
    El archivo se sube a MinIO y en ar_file se guarda solo el object_name.
    """
    __tablename__ = "AnnexedResult"

    ar_id = Column(Integer, primary_key=True, index=True)
    ar_order_id = Column(Integer, ForeignKey("Orders.o_id"), nullable=False)
    ar_file = Column(String(500), nullable=False)
    ar_user_record_file = Column(Integer, ForeignKey("AppUsers.usr_id"), nullable=True)
    ar_external_lab_id = Column(Integer, ForeignKey("ExternalReferenceLaboratories.erl_id"), nullable=True)
    ar_created_at = Column(DateTime, default=get_bogota_now)
    ar_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    # Relaciones
    order = relationship("Order", foreign_keys=[ar_order_id])
    user = relationship("AppUser", foreign_keys=[ar_user_record_file])
    external_lab = relationship("ExternalReferenceLaboratory", foreign_keys=[ar_external_lab_id])

    def __repr__(self):
        return f"<AnnexedResult(id={self.ar_id}, order_id={self.ar_order_id}, file='{self.ar_file}')>"
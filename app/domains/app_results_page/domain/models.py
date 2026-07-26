from sqlalchemy import Column, Integer, SmallInteger, String, Boolean, DateTime
from app.core.database import Base
from utils.timezone import get_bogota_now


class AppResultsPage(Base):
    __tablename__ = "AppResultsPage"

    arp_user_id = Column(Integer, primary_key=True, index=True)
    arp_user_origin_id = Column(Integer, nullable=False)
    arp_user_login = Column(String(255), nullable=False, unique=True, index=True)
    arp_user_active = Column(Boolean, nullable=False, default=True)
    arp_user_mail = Column(String(255), nullable=True)
    arp_user_access_type = Column(SmallInteger, nullable=False)
    arp_user_recovery = Column(Boolean, nullable=False, default=False)
    arp_last_access = Column(DateTime, nullable=True)
    arp_created_at = Column(DateTime, default=get_bogota_now)
    arp_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)

    def __repr__(self):
        return f"<AppResultsPage(id={self.arp_user_id}, login='{self.arp_user_login}', access_type={self.arp_user_access_type})>"

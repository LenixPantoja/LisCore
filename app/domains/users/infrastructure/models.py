from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from utils.timezone import get_bogota_now


class Permission(Base):
    __tablename__ = "Permissions"

    p_id = Column(Integer, primary_key=True, index=True)
    p_name = Column(String(255), unique=True, nullable=False)
    p_description = Column(String(255), nullable=True)
    p_module = Column(String(100), nullable=True)

    roles = relationship("Rol", secondary="RolPermissions", back_populates="permissions")


class RolPermission(Base):
    __tablename__ = "RolPermissions"

    rp_rol_id = Column(Integer, ForeignKey("Rols.r_id", ondelete="CASCADE"), primary_key=True)
    rp_permission_id = Column(Integer, ForeignKey("Permissions.p_id", ondelete="CASCADE"), primary_key=True)
    rp_active = Column(Boolean, default=True, nullable=False)


class Rol(Base):
    __tablename__ = "Rols"

    r_id = Column(Integer, primary_key=True, index=True)
    r_name = Column(String(255))
    r_description = Column(String(255))

    users = relationship("AppUser", back_populates="role")
    permissions = relationship("Permission", secondary="RolPermissions", back_populates="roles")

class AppUser(Base):
    __tablename__ = "AppUsers"

    usr_id = Column(Integer, primary_key=True, index=True)
    usr_login = Column(String(255), unique=True, index=True)
    usr_password = Column(String(255), nullable=False)
    usr_first_name = Column(String(255))
    usr_middle_name = Column(String(255), nullable=True)
    usr_last_name = Column(String(255))
    usr_second_last_name = Column(String(255), nullable=True)
    usr_document_number = Column(String(255), unique=True, index=True)
    usr_phone_number = Column(String(255), nullable=True)
    usr_is_active = Column(Boolean, default=True)
    usr_mail = Column(String(255), unique=True, index=True)
    usr_is_Locked = Column(Boolean, default=False)
    usr_Signature = Column(Text, nullable=True)
    usr_created_at = Column(DateTime, default=get_bogota_now)
    usr_updated_at = Column(DateTime, default=get_bogota_now, onupdate=get_bogota_now)
    usr_rol_id = Column(Integer, ForeignKey("Rols.r_id"), nullable=False)

    role = relationship("Rol", back_populates="users")

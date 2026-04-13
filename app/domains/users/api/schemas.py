from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    usr_login: str
    usr_first_name: str
    usr_middle_name: Optional[str] = None
    usr_last_name: str
    usr_second_last_name: Optional[str] = None
    usr_document_number: str
    usr_phone_number: Optional[str] = None
    usr_is_active: Optional[bool] = True
    usr_mail: EmailStr
    usr_rol_id: int

class UserCreate(UserBase):
    usr_password: str

class UserUpdate(BaseModel):
    usr_login: Optional[str] = None
    usr_first_name: Optional[str] = None
    usr_middle_name: Optional[str] = None
    usr_last_name: Optional[str] = None
    usr_second_last_name: Optional[str] = None
    usr_phone_number: Optional[str] = None
    usr_is_active: Optional[bool] = None
    usr_password: Optional[str] = None
    usr_mail: Optional[EmailStr] = None
    usr_is_Locked: Optional[bool] = None
    usr_Signature: Optional[str] = None
    usr_rol_id: Optional[int] = None

class UserResponse(UserBase):
    usr_id: int
    usr_is_Locked: bool
    usr_created_at: datetime
    usr_updated_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    usr_login: str
    usr_password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    usr_id: int
    usr_login: str
    usr_full_name: str
    usr_rol_name: Optional[str] = None

class UserPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[UserResponse]

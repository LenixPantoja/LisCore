from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    usr_id: Optional[int]
    usr_login: str
    usr_first_name: str
    usr_last_name: str
    usr_mail: str
    usr_rol_id: int
    usr_is_active: bool = True
    usr_middle_name: Optional[str] = None
    usr_second_last_name: Optional[str] = None
    usr_document_number: Optional[str] = None
    usr_phone_number: Optional[str] = None
    usr_password: Optional[str] = None
    usr_is_Locked: bool = False
    usr_Signature: Optional[str] = None
    usr_created_at: Optional[datetime] = None
    usr_updated_at: Optional[datetime] = None
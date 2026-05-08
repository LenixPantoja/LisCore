from abc import ABC, abstractmethod
from typing import Optional
from app.domains.users.domain.models import User

class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_login(self, login: str) -> Optional[User]:
        pass

    @abstractmethod
    async def create(self, user_data: dict) -> User:
        pass

    @abstractmethod
    async def update(self, user: User, update_data: dict) -> User:
        pass
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db
from app.domains.users.api.schemas import UserCreate, UserUpdate, UserResponse, UserLogin
from app.domains.users.application.use_cases import create_user, update_user, login_user # Use cases
from app.domains.users.infrastructure.repository import UserRepository # Concrete repository implementation

router = APIRouter()

@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para iniciar sesión de usuario.
    """
    user_repo = UserRepository() # Instantiate the concrete repository
    return await login_user.execute(user_repo, db, data.model_dump())

@router.post("/", response_model=UserResponse)
async def create_new_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para crear un nuevo usuario.
    """
    user_repo = UserRepository() # Instantiate the concrete repository
    # The use case expects a dict, which Pydantic's model_dump provides.
    # The repository will handle the conversion to ORM model.
    created_user = await create_user.execute(user_repo, db, data.model_dump())
    return UserResponse.model_validate(created_user) # Convert domain model back to response schema

@router.patch("/{user_id}", response_model=UserResponse)
async def update_existing_user(user_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para actualizar un usuario existente.
    """
    user_repo = UserRepository() # Instantiate the concrete repository
    updated_user = await update_user.execute(user_repo, db, user_id, data.model_dump(exclude_unset=True))
    return UserResponse.model_validate(updated_user) # Convert domain model back to response schema

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db
from app.domains.users.api.schemas import UserCreate, UserUpdate, UserResponse, UserLogin
from app.domains.users.application.use_cases import create_user, update_user, login_user

router = APIRouter()

@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Login endpoint. Note: Since the schema lacks a password field, this is simulating 
    login strictly with the username (or expecting an external auth flow).
    """
    return await login_user.execute(db, data.model_dump())

@router.post("/", response_model=UserResponse)
async def create_new_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user endpoint.
    """
    return await create_user.execute(db, data.model_dump())

@router.patch("/{user_id}", response_model=UserResponse)
async def update_existing_user(user_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing user endpoint.
    """
    return await update_user.execute(db, user_id, data.model_dump(exclude_unset=True))

from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.users.api.schemas import UserResponse, UserPaginatedResponse, UserUpdate, UserLogin
from app.domains.users.application.use_cases import list_users, get_user, update_user, login_user
from app.domains.users.infrastructure.repository import UserRepository

router = APIRouter()

@router.get("/", response_model=UserPaginatedResponse)
async def list_existing_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para listar usuarios con paginación y búsqueda opcional por nombre, apellido o login.
    """
    return await list_users.execute(db, skip, limit, search)

@router.get("/{usr_id}", response_model=UserResponse)
async def get_user_details(usr_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener el detalle de un usuario específico por su ID.
    """
    return await get_user.execute(db, usr_id)

@router.patch("/{usr_id}", response_model=UserResponse)
async def update_existing_user(usr_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para actualizar los datos de un usuario existente.
    """
    return await update_user.execute(
        UserRepository, 
        db, 
        usr_id, 
        data.model_dump(exclude_unset=True)
    )

@router.post("/login")
async def login_for_access_token(
    form_data: UserLogin, 
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para autenticar un usuario y obtener un token de acceso.
    """
    return await login_user.execute(UserRepository, db, form_data.model_dump())
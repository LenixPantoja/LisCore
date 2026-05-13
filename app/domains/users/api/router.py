from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.users.api.schemas import (
    UserResponse, UserPaginatedResponse, UserUpdate, UserLogin, LoginResponse,
    PermissionCreate, PermissionUpdate, PermissionResponse, PermissionModuleTreeResponse, RolePermissionAssign,
    RolCreate, RolUpdate, RolResponse, RolWithPermissionsResponse, UserCreate, UserCreateResponse,
)
from app.domains.users.application.use_cases import (
    list_users, get_user, update_user, login_user,
    list_permissions, list_permissions_tree, create_permission, update_permission, delete_permission, role_permissions,
    list_roles, create_role, get_role, update_role, create_user,
)
from app.domains.users.infrastructure.repository import UserRepository, PermissionRepository

router = APIRouter()

# ── Users ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    permission_ids = data.permission_ids
    user_dict = data.model_dump(exclude={"permission_ids"})
    new_user = await create_user.execute(UserRepository, db, user_dict, permission_ids)
    role_perms = await PermissionRepository.get_permissions_by_role(db, new_user.usr_rol_id)
    return {
        **{c.name: getattr(new_user, c.name) for c in new_user.__table__.columns},
        "role": new_user.role,
        "permissions": role_perms,
    }

@router.get("/", response_model=UserPaginatedResponse)
async def list_existing_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await list_users.execute(db, skip, limit, search)

@router.get("/{usr_id}", response_model=UserResponse)
async def get_user_details(usr_id: int, db: AsyncSession = Depends(get_db)):
    return await get_user.execute(db, usr_id)

@router.patch("/{usr_id}", response_model=UserResponse)
async def update_existing_user(usr_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    return await update_user.execute(UserRepository, db, usr_id, data.model_dump(exclude_unset=True))

@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(form_data: UserLogin, db: AsyncSession = Depends(get_db)):
    return await login_user.execute(UserRepository, db, form_data.model_dump())


# ── Permissions ──────────────────────────────────────────────────────────────

@router.get("/permissions/", response_model=List[PermissionResponse], tags=["RBAC"])
async def list_all_permissions(db: AsyncSession = Depends(get_db)):
    return await list_permissions.execute(db)

@router.get("/permissions/tree", response_model=List[PermissionModuleTreeResponse], tags=["RBAC"])
async def list_permissions_by_module(db: AsyncSession = Depends(get_db)):
    return await list_permissions_tree.execute(db)

@router.patch("/permissions/{permission_id}", response_model=PermissionResponse, tags=["RBAC"])
async def update_existing_permission(
    permission_id: int, data: PermissionUpdate, db: AsyncSession = Depends(get_db)
):
    return await update_permission.execute(db, permission_id, data.model_dump(exclude_unset=True))

@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["RBAC"])
async def delete_existing_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    await delete_permission.execute(db, permission_id)


# ── Roles ────────────────────────────────────────────────────────────────────

@router.get("/roles/", response_model=List[RolResponse], tags=["RBAC"])
async def list_all_roles(db: AsyncSession = Depends(get_db)):
    return await list_roles.execute(db)

@router.post("/roles/", response_model=RolWithPermissionsResponse, status_code=status.HTTP_201_CREATED, tags=["RBAC"])
async def create_new_role(data: RolCreate, db: AsyncSession = Depends(get_db)):
    return await create_role.execute(db, data.model_dump())

@router.get("/roles/{rol_id}", response_model=RolWithPermissionsResponse, tags=["RBAC"])
async def get_role_detail(rol_id: int, db: AsyncSession = Depends(get_db)):
    return await get_role.execute(db, rol_id)

@router.patch("/roles/{rol_id}", response_model=RolWithPermissionsResponse, tags=["RBAC"])
async def update_existing_role(rol_id: int, data: RolUpdate, db: AsyncSession = Depends(get_db)):
    return await update_role.execute(db, rol_id, data.model_dump(exclude_unset=True))


# ── Role ↔ Permission ────────────────────────────────────────────────────────

@router.get("/roles/{rol_id}/permissions", response_model=List[PermissionResponse], tags=["RBAC"])
async def get_permissions_for_role(rol_id: int, db: AsyncSession = Depends(get_db)):
    return await role_permissions.execute(db, rol_id)

@router.post(
    "/roles/{rol_id}/permissions",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["RBAC"],
)
async def assign_permission_to_role(
    rol_id: int, body: RolePermissionAssign, db: AsyncSession = Depends(get_db)
):
    await role_permissions.assign(db, rol_id, body.permission_id)

@router.delete(
    "/roles/{rol_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["RBAC"],
)
async def remove_permission_from_role(
    rol_id: int, permission_id: int, db: AsyncSession = Depends(get_db)
):
    await role_permissions.remove(db, rol_id, permission_id)


@router.patch(
    "/roles/{rol_id}/permissions/{permission_id}/active",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["RBAC"],
)
async def toggle_role_permission_active(
    rol_id: int,
    permission_id: int,
    active: bool,
    db: AsyncSession = Depends(get_db),
):
    await role_permissions.toggle_active(db, rol_id, permission_id, active)
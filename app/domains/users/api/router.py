import os
from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query, Form, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.users.api.schemas import (
    UserResponse, UserPaginatedResponse, UserUpdate, UserLogin, LoginResponse,
    PermissionCreate, PermissionUpdate, PermissionResponse, PermissionModuleTreeResponse, RolePermissionAssign,
    RolCreate, RolUpdate, RolResponse, RolWithPermissionsResponse, UserCreate, UserCreateResponse, UserDetailResponse,
)
from app.domains.users.application.use_cases import (
    list_users, get_user, update_user, login_user,
    list_permissions, list_permissions_tree, create_permission, update_permission, delete_permission, role_permissions,
    list_roles, create_role, get_role, update_role, create_user,
)
from app.domains.users.infrastructure.repository import UserRepository, PermissionRepository

router = APIRouter()

# ── Users ────────────────────────────────────────────────────────────────────

ALLOWED_SIGNATURE_TYPES = {"image/png", "image/jpeg", "image/jpg"}


@router.post("/", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("AppUsers:Create"))])
async def create_new_user(
    usr_login: str = Form(...),
    usr_first_name: str = Form(...),
    usr_middle_name: Optional[str] = Form(None),
    usr_last_name: str = Form(...),
    usr_second_last_name: Optional[str] = Form(None),
    usr_document_number: str = Form(...),
    usr_phone_number: Optional[str] = Form(None),
    usr_is_active: bool = Form(True),
    usr_mail: str = Form(...),
    usr_rol_id: int = Form(...),
    usr_password: str = Form(...),
    permission_ids: Optional[List[int]] = Form(None),
    signature: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    if signature is not None and signature.content_type not in ALLOWED_SIGNATURE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo de archivo no permitido. Se aceptan: {', '.join(ALLOWED_SIGNATURE_TYPES)}",
        )

    signature_bytes: Optional[bytes] = None
    signature_extension: str = "png"
    if signature is not None:
        signature_bytes = await signature.read()
        signature_extension = os.path.splitext(signature.filename or "sign.png")[1].lstrip(".") or "png"

    user_dict = {
        "usr_login": usr_login,
        "usr_first_name": usr_first_name,
        "usr_middle_name": usr_middle_name,
        "usr_last_name": usr_last_name,
        "usr_second_last_name": usr_second_last_name,
        "usr_document_number": usr_document_number,
        "usr_phone_number": usr_phone_number,
        "usr_is_active": usr_is_active,
        "usr_mail": usr_mail,
        "usr_rol_id": usr_rol_id,
        "usr_password": usr_password,
    }

    new_user = await create_user.execute(
        UserRepository, db, user_dict, permission_ids, signature_bytes, signature_extension
    )
    role_perms = await PermissionRepository.get_permissions_by_role(db, new_user.usr_rol_id)
    return {
        **{c.name: getattr(new_user, c.name) for c in new_user.__table__.columns},
        "role": new_user.role,
        "permissions": role_perms,
    }

@router.get("/", response_model=UserPaginatedResponse,
            dependencies=[Depends(require_permission("AppUsers:List"))])
async def list_existing_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await list_users.execute(db, skip, limit, search)

@router.get("/{usr_id}", response_model=UserDetailResponse,
            dependencies=[Depends(require_permission("AppUsers:GetOne"))])
async def get_user_details(usr_id: int, db: AsyncSession = Depends(get_db)):
    return await get_user.execute(db, usr_id)

@router.patch("/{usr_id}", response_model=UserCreateResponse,
              dependencies=[Depends(require_permission("AppUsers:Update"))])
async def update_existing_user(
    usr_id: int,
    usr_login: Optional[str] = Form(None),
    usr_first_name: Optional[str] = Form(None),
    usr_middle_name: Optional[str] = Form(None),
    usr_last_name: Optional[str] = Form(None),
    usr_second_last_name: Optional[str] = Form(None),
    usr_phone_number: Optional[str] = Form(None),
    usr_is_active: Optional[bool] = Form(None),
    usr_password: Optional[str] = Form(None),
    usr_mail: Optional[str] = Form(None),
    usr_is_Locked: Optional[bool] = Form(None),
    usr_rol_id: Optional[int] = Form(None),
    permission_ids: Optional[List[int]] = Form(None),
    signature: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    if signature is not None and signature.content_type not in ALLOWED_SIGNATURE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo de archivo no permitido. Se aceptan: {', '.join(ALLOWED_SIGNATURE_TYPES)}",
        )

    signature_bytes: Optional[bytes] = None
    signature_extension: str = "png"
    if signature is not None:
        signature_bytes = await signature.read()
        signature_extension = os.path.splitext(signature.filename or "sign.png")[1].lstrip(".") or "png"

    update_data = {
        k: v for k, v in {
            "usr_login": usr_login,
            "usr_first_name": usr_first_name,
            "usr_middle_name": usr_middle_name,
            "usr_last_name": usr_last_name,
            "usr_second_last_name": usr_second_last_name,
            "usr_phone_number": usr_phone_number,
            "usr_is_active": usr_is_active,
            "usr_password": usr_password,
            "usr_mail": usr_mail,
            "usr_is_Locked": usr_is_Locked,
            "usr_rol_id": usr_rol_id,
            "permission_ids": permission_ids,
        }.items() if v is not None
    }

    updated_user = await update_user.execute(
        UserRepository, db, usr_id, update_data, signature_bytes, signature_extension
    )
    role_perms = await PermissionRepository.get_permissions_by_role(db, updated_user.usr_rol_id)
    return {
        **{c.name: getattr(updated_user, c.name) for c in updated_user.__table__.columns},
        "role": updated_user.role,
        "permissions": role_perms,
    }

@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(form_data: UserLogin, db: AsyncSession = Depends(get_db)):
    return await login_user.execute(UserRepository, db, form_data.model_dump())


# ── Permissions ──────────────────────────────────────────────────────────────

@router.get("/permissions/", response_model=List[PermissionResponse], tags=["RBAC"],
            dependencies=[Depends(require_permission("Permissions:Read"))])
async def list_all_permissions(db: AsyncSession = Depends(get_db)):
    return await list_permissions.execute(db)

@router.get("/permissions/tree", response_model=List[PermissionModuleTreeResponse], tags=["RBAC"],
            dependencies=[Depends(require_permission("Permissions:Read"))])
async def list_permissions_by_module(db: AsyncSession = Depends(get_db)):
    return await list_permissions_tree.execute(db)

@router.patch("/permissions/{permission_id}", response_model=PermissionResponse, tags=["RBAC"],
              dependencies=[Depends(require_permission("Permissions:Write"))])
async def update_existing_permission(
    permission_id: int, data: PermissionUpdate, db: AsyncSession = Depends(get_db)
):
    return await update_permission.execute(db, permission_id, data.model_dump(exclude_unset=True))

@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["RBAC"],
               dependencies=[Depends(require_permission("Permissions:Write"))])
async def delete_existing_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    await delete_permission.execute(db, permission_id)


# ── Roles ────────────────────────────────────────────────────────────────────

@router.get("/roles/", response_model=List[RolResponse], tags=["RBAC"],
            dependencies=[Depends(require_permission("Rols:Read"))])
async def list_all_roles(db: AsyncSession = Depends(get_db)):
    return await list_roles.execute(db)

@router.post("/roles/", response_model=RolWithPermissionsResponse, status_code=status.HTTP_201_CREATED, tags=["RBAC"],
             dependencies=[Depends(require_permission("Rols:Create"))])
async def create_new_role(data: RolCreate, db: AsyncSession = Depends(get_db)):
    return await create_role.execute(db, data.model_dump())

@router.get("/roles/{rol_id}", response_model=RolWithPermissionsResponse, tags=["RBAC"],
            dependencies=[Depends(require_permission("Rols:Read"))])
async def get_role_detail(rol_id: int, db: AsyncSession = Depends(get_db)):
    return await get_role.execute(db, rol_id)

@router.patch("/roles/{rol_id}", response_model=RolWithPermissionsResponse, tags=["RBAC"],
              dependencies=[Depends(require_permission("Rols:Update"))])
async def update_existing_role(rol_id: int, data: RolUpdate, db: AsyncSession = Depends(get_db)):
    return await update_role.execute(db, rol_id, data.model_dump(exclude_unset=True))


# ── Role ↔ Permission ────────────────────────────────────────────────────────

@router.get("/roles/{rol_id}/permissions", response_model=List[PermissionResponse], tags=["RBAC"],
            dependencies=[Depends(require_permission("Rols:Read"))])
async def get_permissions_for_role(rol_id: int, db: AsyncSession = Depends(get_db)):
    return await role_permissions.execute(db, rol_id)

@router.post(
    "/roles/{rol_id}/permissions",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["RBAC"],
    dependencies=[Depends(require_permission("AppUserPermissions:Vinculate"))],
)
async def assign_permission_to_role(
    rol_id: int, body: RolePermissionAssign, db: AsyncSession = Depends(get_db)
):
    await role_permissions.assign(db, rol_id, body.permission_id)
    from app.core.dependencies import invalidate_permission_cache
    invalidate_permission_cache(rol_id)

@router.delete(
    "/roles/{rol_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["RBAC"],
    dependencies=[Depends(require_permission("AppUserPermissions:Vinculate"))],
)
async def remove_permission_from_role(
    rol_id: int, permission_id: int, db: AsyncSession = Depends(get_db)
):
    await role_permissions.remove(db, rol_id, permission_id)
    from app.core.dependencies import invalidate_permission_cache
    invalidate_permission_cache(rol_id)


@router.patch(
    "/roles/{rol_id}/permissions/{permission_id}/active",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["RBAC"],
    dependencies=[Depends(require_permission("AppUserPermissions:Vinculate"))],
)
async def toggle_role_permission_active(
    rol_id: int,
    permission_id: int,
    active: bool,
    db: AsyncSession = Depends(get_db),
):
    await role_permissions.toggle_active(db, rol_id, permission_id, active)
    from app.core.dependencies import invalidate_permission_cache
    invalidate_permission_cache(rol_id)
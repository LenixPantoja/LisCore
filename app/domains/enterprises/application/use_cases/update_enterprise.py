from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.enterprises.infrastructure.repository import EnterpriseRepository
from app.core.security import get_password_hash
from fastapi import HTTPException, status

async def execute(db: AsyncSession, enterprise_id: int, update_data: dict):
    # 1. Verificar si la empresa existe
    enterprise = await EnterpriseRepository.get_by_id(db, enterprise_id)
    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enterprise not found"
        )

    # 2. Validaciones de unicidad si se intentan cambiar campos clave
    if "en_code" in update_data and update_data["en_code"] != enterprise.en_code:
        if await EnterpriseRepository.get_by_code(db, update_data["en_code"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New enterprise code already registered"
            )

    if "en_nit" in update_data and update_data["en_nit"] != enterprise.en_nit:
        if await EnterpriseRepository.get_by_nit(db, update_data["en_nit"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New NIT already registered"
            )

    if "en_mail" in update_data and update_data["en_mail"] != enterprise.en_mail:
        if await EnterpriseRepository.get_by_mail(db, update_data["en_mail"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New email already registered"
            )

    # 3. Hashear password si se está actualizando
    if update_data.get("en_password"):
        update_data["en_password"] = get_password_hash(update_data["en_password"])

    # 4. Realizar la actualización
    return await EnterpriseRepository.update(db, enterprise, update_data)
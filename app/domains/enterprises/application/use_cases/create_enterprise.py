from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.enterprises.infrastructure.repository import EnterpriseRepository
from app.domains.app_results_page.application.use_cases.app_results_page_use_cases import provision_for_enterprise
from app.core.security import get_password_hash
from fastapi import HTTPException, status

async def execute(db: AsyncSession, enterprise_data: dict):
    """
    Executes the use case for creating a new enterprise.
    Checks for existing enterprises by code, NIT, and email before creation.
    """
    # Check if enterprise already exists by code
    existing_enterprise_by_code = await EnterpriseRepository.get_by_code(db, enterprise_data["en_code"])
    if existing_enterprise_by_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enterprise with this code already registered"
        )
    
    # Check if enterprise already exists by NIT
    existing_enterprise_by_nit = await EnterpriseRepository.get_by_nit(db, enterprise_data["en_nit"])
    if existing_enterprise_by_nit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enterprise with this NIT already registered"
        )
    
    # Check if enterprise already exists by email if provided
    if enterprise_data.get("en_mail"):
        existing_enterprise_by_mail = await EnterpriseRepository.get_by_mail(db, enterprise_data["en_mail"])
        if existing_enterprise_by_mail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enterprise with this email already registered"
            )

    # Password por defecto: el NIT, siempre hasheada
    raw_password = enterprise_data.get("en_password") or enterprise_data.get("en_nit")
    enterprise_data["en_password"] = get_password_hash(raw_password)

    # Create the new enterprise
    new_enterprise = await EnterpriseRepository.create(db, enterprise_data)
    await provision_for_enterprise(db, new_enterprise)
    return new_enterprise
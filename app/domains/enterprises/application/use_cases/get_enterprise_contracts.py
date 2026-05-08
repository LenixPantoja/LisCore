from typing import Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.domains.enterprises.infrastructure.repository import EnterpriseRepository
from app.domains.contractstariffs.infrastructure.repository import ContractTariffRepository
from app.domains.contractstariffs.domain.models import Contract


async def execute(
    db: AsyncSession,
    enterprise_id: int,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    active: Optional[bool] = None,
) -> Tuple[Sequence[Contract], int]:
    enterprise = await EnterpriseRepository.get_by_id(db, enterprise_id)
    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enterprise not found",
        )

    return await ContractTariffRepository.get_contracts_with_tariffs_by_enterprise(
        db, enterprise_id, skip, limit, search, active
    )

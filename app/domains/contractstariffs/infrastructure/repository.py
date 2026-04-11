from typing import Tuple, Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.domains.contractstariffs.domain.models import Contract

class ContractTariffRepository:
    @staticmethod
    async def get_contracts_paginated(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None,
        enterprise_id: Optional[int] = None
    ) -> Tuple[Sequence[Contract], int]:
        query = select(Contract)
        
        # Filtros de búsqueda
        if search:
            query = query.filter(Contract.co_code.ilike(f"%{search}%"))
        
        if enterprise_id:
            query = query.filter(Contract.co_enterprise_id == enterprise_id)
        
        # Conteo total para paginación
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        # Resultados paginados
        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Contract.co_code.asc())
        )
        return result.scalars().all(), total

    # ... otros métodos (create_contract, link_tariff_to_contract, etc.)
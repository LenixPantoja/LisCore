from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.contractstariffs.infrastructure.repository import ContractTariffRepository
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

async def create_tariff(db: AsyncSession, data: dict):
    return await ContractTariffRepository.create_tariff(db, data)

async def list_tariffs(db: AsyncSession):
    return await ContractTariffRepository.get_tariffs(db)

async def add_detail_to_tariff(db: AsyncSession, tariff_id: int, data: dict):
    try:
        return await ContractTariffRepository.add_tariff_detail(db, tariff_id, data)
    except IntegrityError as e:
        await db.rollback()
        error_detail = str(e.orig)
        
        if "td_studie_id" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El ID de estudio {data.get('td_studie_id')} no existe en el catálogo médico (StudiesLab)."
            )
        
        if "td_tariff_id" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La tarifa con ID {tariff_id} no fue encontrada."
            )
            
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad: verifique que los IDs de tarifa y estudio sean válidos."
        )

async def create_contract(db: AsyncSession, data: dict):
    return await ContractTariffRepository.create_contract(db, data)

async def list_contracts(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None, enterprise_id: int = None):
    items, total = await ContractTariffRepository.get_contracts_paginated(db, skip, limit, search, enterprise_id)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def link_tariff_to_contract(db: AsyncSession, data: dict):
    try:
        return await ContractTariffRepository.link_tariff_to_contract(db, data)
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig)
        if "ct_contract_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El contrato especificado no existe.")
        if "ct_tariff_id" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarifa especificada no existe.")
            
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad al vincular la tarifa con el contrato."
        )

async def get_contract_tariffs(db: AsyncSession, contract_id: int):
    return await ContractTariffRepository.get_contract_tariffs(db, contract_id)
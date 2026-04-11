from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.domains.contractstariffs.api.schemas import ContractPaginatedResponse, ContractResponse, ContractBase
from app.domains.contractstariffs.application.use_cases import tariff_contracts_use_cases

router = APIRouter()

# --- Tariffs (Tarifas) ---

@router.post("/tariffs", status_code=status.HTTP_201_CREATED)
async def create_new_tariff(data: dict, db: AsyncSession = Depends(get_db)):
    return await tariff_contracts_use_cases.create_tariff(db, data)

@router.get("/tariffs")
async def list_all_tariffs(db: AsyncSession = Depends(get_db)):
    return await tariff_contracts_use_cases.list_tariffs(db)

@router.post("/tariffs/{tariff_id}/details", status_code=status.HTTP_201_CREATED)
async def add_detail_to_tariff(tariff_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    return await tariff_contracts_use_cases.add_detail_to_tariff(db, tariff_id, data)

# --- Contracts (Contratos) ---

@router.post("/contracts", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_new_contract(data: ContractBase, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para crear un nuevo contrato.
    """
    return await tariff_contracts_use_cases.create_contract(db, data.model_dump())

@router.get("/contracts", response_model=ContractPaginatedResponse)
async def list_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    enterprise_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para listar contratos con paginación y búsqueda opcional.
    """
    return await tariff_contracts_use_cases.list_contracts(
        db, skip, limit, search, enterprise_id
    )

@router.post("/contracts/link-tariff", status_code=status.HTTP_200_OK)
async def link_tariff_to_contract(data: dict, db: AsyncSession = Depends(get_db)):
    return await tariff_contracts_use_cases.link_tariff_to_contract(db, data)

@router.get("/contracts/{contract_id}/tariffs")
async def get_contract_tariffs(contract_id: int, db: AsyncSession = Depends(get_db)):
    return await tariff_contracts_use_cases.get_contract_tariffs(db, contract_id)
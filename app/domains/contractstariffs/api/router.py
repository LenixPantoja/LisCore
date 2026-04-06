from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.domains.contractstariffs.api.schemas import (
    TariffCreate, TariffResponse, TariffDetailCreate, TariffDetailResponse,
    ContractCreate, ContractResponse, ContractTariffCreate, ContractTariffResponse
)
from app.domains.contractstariffs.application.use_cases import tariff_contracts_use_cases as use_cases

router = APIRouter()

# --- Tariffs ---
@router.post("/tariffs", response_model=TariffResponse, status_code=status.HTTP_201_CREATED)
async def create_tariff(data: TariffCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_tariff(db, data.model_dump())

@router.get("/tariffs", response_model=List[TariffResponse])
async def list_tariffs(db: AsyncSession = Depends(get_db)):
    return await use_cases.list_tariffs(db)

@router.post("/tariffs/{tariff_id}/details", response_model=TariffDetailResponse)
async def add_tariff_detail(tariff_id: int, data: TariffDetailCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.add_detail_to_tariff(db, tariff_id, data.model_dump())

# --- Contracts ---
@router.post("/contracts", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(data: ContractCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.create_contract(db, data.model_dump())

@router.get("/contracts", response_model=List[ContractResponse])
async def list_contracts(enterprise_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    return await use_cases.list_contracts(db, enterprise_id)

# --- Linking ---
@router.post("/contract-links", response_model=ContractTariffResponse)
async def link_tariff_to_contract(data: ContractTariffCreate, db: AsyncSession = Depends(get_db)):
    return await use_cases.link_tariff_to_contract(db, data.model_dump())

@router.get("/contracts/{contract_id}/tariffs", response_model=List[ContractTariffResponse])
async def get_contract_tariffs(contract_id: int, db: AsyncSession = Depends(get_db)):
    return await use_cases.get_contract_tariffs(db, contract_id)
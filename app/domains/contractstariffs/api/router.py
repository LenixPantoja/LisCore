from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.domains.contractstariffs.api.schemas import (
    ContractPaginatedResponse,
    ContractResponse,
    ContractCreate,
    ContractUpdate,
    TariffCreate,
    TariffUpdate,
    TariffResponse,
    TariffPaginatedResponse,
    TariffDetailBase,
    TariffDetailResponse,
    TariffDetailUpdate,
    TariffDetailWithStudieResponse,
    TariffDetailPaginatedResponse,
    LinkTariffToContractRequest,
    ContractTariffResponse,
    UnlinkTariffFromContractRequest,
    UnlinkTariffFromContractResponse,
    EnterpriseTariffStudiesResponse
)
from app.domains.contractstariffs.application.use_cases import tariff_contracts_use_cases

router = APIRouter()

# --- Tariffs (Tarifas) ---

@router.post("/tariffs", response_model=TariffResponse, status_code=status.HTTP_201_CREATED)
async def create_new_tariff(data: TariffCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new tariff with optional details.
    
    - **t_name**: Name of the tariff (required)
    - **t_description**: Description of the tariff (optional)
    - **t_activo**: Whether the tariff is active (default: True)
    - **details**: List of tariff details with study IDs and values (optional)
    """
    return await tariff_contracts_use_cases.create_tariff(db, data.model_dump())

@router.get("/tariffs", response_model=List[TariffResponse])
async def list_all_tariffs(db: AsyncSession = Depends(get_db)):
    """
    Get all tariffs with their details.
    """
    return await tariff_contracts_use_cases.list_tariffs(db)

@router.get("/enterprises/{enterprise_id}/tariffs", response_model=TariffPaginatedResponse)
async def list_tariffs_by_enterprise(
    enterprise_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all tariffs associated with an enterprise via its contracts.

    - **enterprise_id**: Enterprise ID (path parameter)
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by tariff name (case-insensitive)
    - **active**: Filter by active status
    """
    return await tariff_contracts_use_cases.list_tariffs_by_enterprise(
        db, enterprise_id, skip, limit, search, active
    )

@router.get("/enterprises/{enterprise_id}/tariffs/{tariff_id}/studies", response_model=EnterpriseTariffStudiesResponse)
async def list_tariff_studies_by_enterprise(
    enterprise_id: int,
    tariff_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all studies associated with a specific tariff for an enterprise, including tariff values.

    - **enterprise_id**: Enterprise ID (path parameter)
    - **tariff_id**: Tariff ID (path parameter)
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (1-500)
    - **search**: Filter by study name or code (case-insensitive)
    - **active**: Filter by study active status

    Returns full study information with the tariff detail value.
    """
    return await tariff_contracts_use_cases.get_tariff_studies_by_enterprise(
        db, enterprise_id, tariff_id, skip, limit, search, active
    )

@router.get("/tariffs/paginated", response_model=TariffPaginatedResponse)
async def list_tariffs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tariffs with pagination and optional filters.
    
    - **skip**: Number of records to skip (pagination offset)
    - **limit**: Maximum number of records to return (1-500)
    - **search**: Filter by tariff name (case-insensitive)
    - **active**: Filter by active status (True/False)
    """
    return await tariff_contracts_use_cases.list_tariffs_paginated(
        db, skip, limit, search, active
    )

@router.get("/tariffs/{tariff_id}", response_model=TariffResponse)
async def get_tariff(tariff_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a tariff by ID with its details.
    """
    return await tariff_contracts_use_cases.get_tariff_by_id(db, tariff_id)

@router.get("/tariffs/{tariff_id}/details", response_model=TariffDetailPaginatedResponse)
async def list_tariff_details(
    tariff_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all details of a tariff with pagination and study information.

    - **tariff_id**: Tariff ID (required, path parameter)
    - **skip**: Number of records to skip (pagination offset)
    - **limit**: Maximum number of records to return (1-500)
    - **search**: Filter by study name or code (case-insensitive)
    - **active**: Filter by study active status (True/False)

    Returns each detail line with its linked study info (id, code, name, active).
    """
    return await tariff_contracts_use_cases.get_tariff_details_paginated(
        db, tariff_id, skip, limit, search, active
    )

@router.post("/tariffs/{tariff_id}/details", response_model=TariffDetailResponse, status_code=status.HTTP_201_CREATED)
async def add_detail_to_tariff(tariff_id: int, data: TariffDetailBase, db: AsyncSession = Depends(get_db)):
    """
    Add a detail line to an existing tariff.

    - **td_studie_id**: Study ID to link (required)
    - **td_value**: Value for the study (required)

    **Errors:**
    - 404: Tariff not found
    - 400: Study ID does not exist in StudiesLab catalog
    """
    return await tariff_contracts_use_cases.add_detail_to_tariff(db, tariff_id, data.model_dump())

@router.patch("/tariffs/details/{detail_id}", response_model=TariffDetailWithStudieResponse)
async def update_tariff_detail(detail_id: int, data: TariffDetailUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update a tariff detail.

    Only sends the fields you want to update. Unset fields remain unchanged.

    - **td_studie_id**: Study ID to link
    - **td_value**: Value for the study

    **Errors:**
    - 404: Detail not found
    """
    return await tariff_contracts_use_cases.update_tariff_detail(db, detail_id, data.model_dump(exclude_unset=True))

@router.delete("/tariffs/details/{detail_id}", status_code=status.HTTP_200_OK)
async def delete_tariff_detail(detail_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete (unlink) a tariff detail.

    **Errors:**
    - 404: Detail not found
    """
    return await tariff_contracts_use_cases.delete_tariff_detail(db, detail_id)

@router.patch("/tariffs/{tariff_id}", response_model=TariffResponse)
async def update_tariff(tariff_id: int, data: TariffUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update a tariff's information.
    
    Only sends the fields you want to update. Unset fields remain unchanged.
    """
    return await tariff_contracts_use_cases.update_tariff(db, tariff_id, data.model_dump(exclude_unset=True))

@router.delete("/tariffs/{tariff_id}", status_code=status.HTTP_200_OK)
async def delete_tariff(tariff_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a tariff and its associated details.
    
    **Important**: A tariff can only be deleted if it is NOT being used in any orders.
    If the tariff is in use, a 409 Conflict error will be returned with details.
    """
    return await tariff_contracts_use_cases.delete_tariff(db, tariff_id)

# --- Contracts (Contratos) ---

@router.post("/contracts", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_new_contract(data: ContractCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new contract.

    - **co_code**: Contract code (optional)
    - **co_observations**: Observations (optional)
    - **co_value_contracted**: Contracted value (optional)
    - **co_value_consumed**: Consumed value (optional)
    - **co_value_alarm**: Alarm value (optional)
    - **co_billing_type**: Billing type (optional)
    - **co_contract_number**: Contract number (optional)
    - **co_number_poliza**: Policy number (optional)
    - **co_active**: Whether the contract is active (default: True)
    - **co_enterprise_id**: Enterprise ID (optional, FK to Enterprises)
    """
    return await tariff_contracts_use_cases.create_contract(db, data.model_dump())

@router.patch("/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(contract_id: int, data: ContractUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update a contract's information.

    Only sends the fields you want to update. Unset fields remain unchanged.

    - **co_code**: Contract code
    - **co_observations**: Observations
    - **co_value_contracted**: Contracted value
    - **co_value_consumed**: Consumed value
    - **co_value_alarm**: Alarm value
    - **co_billing_type**: Billing type
    - **co_contract_number**: Contract number
    - **co_number_poliza**: Policy number
    - **co_active**: Whether the contract is active
    - **co_enterprise_id**: Enterprise ID

    **Errors:**
    - 404: Contract not found
    """
    return await tariff_contracts_use_cases.update_contract(db, contract_id, data.model_dump(exclude_unset=True))

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

@router.get("/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a contract by ID with its enterprise information and linked tariffs.

    Returns the full contract details including:
    - Contract fields (code, observations, values, etc.)
    - Enterprise information (name, code)
    - List of linked tariffs
    """
    return await tariff_contracts_use_cases.get_contract_by_id(db, contract_id)

@router.post("/contracts/link-tariff", response_model=ContractTariffResponse, status_code=status.HTTP_201_CREATED)
async def link_tariff_to_contract(data: LinkTariffToContractRequest, db: AsyncSession = Depends(get_db)):
    """
    Link a tariff to a contract.

    - **ct_contract_id**: Contract ID (required)
    - **ct_tariff_id**: Tariff ID (required)
    - **ct_active**: Whether the link is active (default: True)
    - **ct_start_date**: Start date (optional, format: YYYY-MM-DD)
    - **ct_end_date**: End date (optional, format: YYYY-MM-DD)

    Returns the created ContractTariff link object.

    **Errors:**
    - 404: Contract or Tariff not found
    - 409: Tariff already linked to this contract
    """
    return await tariff_contracts_use_cases.link_tariff_to_contract(db, data.model_dump())

@router.delete("/contracts/unlink-tariff", response_model=UnlinkTariffFromContractResponse, status_code=status.HTTP_200_OK)
async def unlink_tariff_from_contract(data: UnlinkTariffFromContractRequest, db: AsyncSession = Depends(get_db)):
    """
    Unlink (remove) a tariff from a contract.

    - **ct_contract_id**: Contract ID (required)
    - **ct_tariff_id**: Tariff ID (required)

    **Important**: A tariff can only be unlinked from a contract if the tariff 
    is NOT being used in any orders.

    **Errors:**
    - 404: Contract, Tariff, or Link not found
    - 409: Tariff is being used in orders (check X-Orders-Count header)
    """
    return await tariff_contracts_use_cases.unlink_tariff_from_contract(
        db, data.ct_contract_id, data.ct_tariff_id
    )

@router.get("/contracts/{contract_id}/tariffs")
async def get_contract_tariffs(contract_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get all tariffs linked to a specific contract.
    """
    return await tariff_contracts_use_cases.get_contract_tariffs(db, contract_id)
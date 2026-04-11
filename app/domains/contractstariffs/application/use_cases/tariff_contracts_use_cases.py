from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.contractstariffs.infrastructure.repository import ContractTariffRepository
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from typing import Optional, List

async def create_tariff(db: AsyncSession, data: dict):
    """Create a new tariff with optional details"""
    try:
        return await ContractTariffRepository.create_tariff(db, data)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al crear la tarifa: {str(e.orig)}"
        )

async def list_tariffs(db: AsyncSession) -> List:
    """Get all tariffs"""
    return await ContractTariffRepository.get_tariffs(db)

async def list_tariffs_paginated(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = None,
    active: Optional[bool] = None
):
    """Get tariffs with pagination and optional filters"""
    items, total = await ContractTariffRepository.get_tariffs_paginated(db, skip, limit, search, active)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_tariff_by_id(db: AsyncSession, tariff_id: int):
    """Get a tariff by ID"""
    tariff = await ContractTariffRepository.get_tariff_by_id(db, tariff_id)
    if not tariff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarifa con ID {tariff_id} no encontrada"
        )
    return tariff

async def get_tariff_details_paginated(
    db: AsyncSession,
    tariff_id: int,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active: Optional[bool] = None
):
    """Get tariff details with pagination and study info"""
    # Verify tariff exists
    tariff = await ContractTariffRepository.get_tariff_by_id(db, tariff_id)
    if not tariff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarifa con ID {tariff_id} no encontrada"
        )

    items, total = await ContractTariffRepository.get_tariff_details_paginated(
        db, tariff_id, skip, limit, search, active
    )
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def add_detail_to_tariff(db: AsyncSession, tariff_id: int, data: dict):
    """Add a detail to an existing tariff"""
    # Verify tariff exists
    tariff = await ContractTariffRepository.get_tariff_by_id(db, tariff_id)
    if not tariff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarifa con ID {tariff_id} no encontrada"
        )
    
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

async def update_tariff_detail(db: AsyncSession, detail_id: int, update_data: dict):
    """Update a tariff detail"""
    detail = await ContractTariffRepository.update_tariff_detail(db, detail_id, update_data)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detalle de tarifa con ID {detail_id} no encontrado"
        )
    return detail

async def delete_tariff_detail(db: AsyncSession, detail_id: int):
    """Delete a tariff detail"""
    result = await ContractTariffRepository.delete_tariff_detail(db, detail_id)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    return result

async def update_tariff(db: AsyncSession, tariff_id: int, update_data: dict):
    """Update a tariff"""
    tariff = await ContractTariffRepository.get_tariff_by_id(db, tariff_id)
    if not tariff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarifa con ID {tariff_id} no encontrada"
        )
    
    return await ContractTariffRepository.update_tariff(db, tariff_id, update_data)

async def delete_tariff(db: AsyncSession, tariff_id: int):
    """Delete a tariff (only if not used in orders)"""
    result = await ContractTariffRepository.delete_tariff(db, tariff_id)
    
    if not result["success"]:
        if "no encontrada" in result["message"].lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )
        # Tariff is used in orders
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result["message"],
            headers={"X-Orders-Count": str(result.get("orders_count", 0))}
        )
    
    return result

async def create_contract(db: AsyncSession, data: dict):
    """Create a new contract"""
    return await ContractTariffRepository.create_contract(db, data)

async def update_contract(db: AsyncSession, contract_id: int, update_data: dict):
    """Update a contract"""
    contract = await ContractTariffRepository.update_contract(db, contract_id, update_data)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contrato con ID {contract_id} no encontrado"
        )
    return contract

async def list_contracts(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None, enterprise_id: int = None):
    """List contracts with pagination"""
    items, total = await ContractTariffRepository.get_contracts_paginated(db, skip, limit, search, enterprise_id)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_contract_by_id(db: AsyncSession, contract_id: int):
    """Get a contract by ID with details"""
    contract = await ContractTariffRepository.get_contract_by_id(db, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contrato con ID {contract_id} no encontrado"
        )
    return contract

async def link_tariff_to_contract(db: AsyncSession, data: dict):
    """Link a tariff to a contract"""
    result = await ContractTariffRepository.link_tariff_to_contract(db, data)

    if not result["success"]:
        # Check if it's a 404 error (contract or tariff not found)
        if "no existe" in result["message"].lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )
        # Check if it's a 409 conflict (already linked)
        if "ya está vinculada" in result["message"].lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result["message"]
            )
        # Generic bad request for other errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return result["link"]

async def get_contract_tariffs(db: AsyncSession, contract_id: int):
    """Get all tariffs linked to a contract"""
    return await ContractTariffRepository.get_contract_tariffs(db, contract_id)

async def unlink_tariff_from_contract(db: AsyncSession, contract_id: int, tariff_id: int):
    """Unlink a tariff from a contract (only if not used in orders)"""
    result = await ContractTariffRepository.unlink_tariff_from_contract(db, contract_id, tariff_id)

    if not result["success"]:
        # Check if it's a 404 error (contract or tariff not found)
        if "no existe" in result["message"].lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )
        # Check if it's a 404 error (link not found)
        if "no está vinculada" in result["message"].lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )
        # Check if it's a 409 conflict (tariff used in orders)
        if "siendo usada" in result["message"].lower() or "orden" in result["message"].lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result["message"],
                headers={"X-Orders-Count": str(result.get("orders_count", 0))}
            )
        # Generic bad request for other errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return result
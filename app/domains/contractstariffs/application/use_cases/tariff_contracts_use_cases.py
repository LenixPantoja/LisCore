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

async def list_tariffs_by_enterprise(
    db: AsyncSession,
    enterprise_id: int,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active: Optional[bool] = None
):
    """Get tariffs associated with an enterprise via contracts"""
    items, total = await ContractTariffRepository.get_tariffs_by_enterprise(
        db, enterprise_id, skip, limit, search, active
    )
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

async def get_tariff_studies_by_enterprise(
    db: AsyncSession,
    enterprise_id: int,
    tariff_id: int,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active: Optional[bool] = None
):
    """Get studies for a tariff associated with an enterprise"""
    rows, total, tariff_name = await ContractTariffRepository.get_tariff_studies_by_enterprise(
        db, enterprise_id, tariff_id, skip, limit, search, active
    )
    if not rows and total == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la tarifa {tariff_id} asociada a la empresa {enterprise_id}"
        )

    items = []
    for detail, study in rows:
        items.append({
            "id": study.id,
            "code": study.code,
            "cups_code": study.cups_code if study.cups_code is not None else "-",
            "name": study.name,
            "active": study.active,
            "order_of_print": study.order_of_print,
            "referral_location_id": study.referral_location_id,
            "work_groups_id": study.work_groups_id,
            "td_value": float(detail.td_value),
            "td_id": detail.td_id
        })

    return {
        "enterprise_id": enterprise_id,
        "tariff_id": tariff_id,
        "tariff_name": tariff_name,
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

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


async def list_contracts_by_enterprise(
    db: AsyncSession,
    enterprise_id: int,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active: Optional[bool] = None
):
    """List paginated contracts for a given enterprise, each with its linked tariffs."""
    contracts, total = await ContractTariffRepository.get_contracts_with_tariffs_by_enterprise(
        db, enterprise_id, skip, limit, search, active
    )

    items = []
    for contract in contracts:
        tariffs = []
        for ct_link in contract.tariffs_link:
            if ct_link.tariff:
                tariffs.append({
                    "t_id": ct_link.tariff.t_id,
                    "t_name": ct_link.tariff.t_name,
                    "t_description": ct_link.tariff.t_description,
                    "t_activo": ct_link.tariff.t_activo,
                    "ct_id": ct_link.ct_id,
                    "ct_active": ct_link.ct_active,
                    "ct_start_date": ct_link.ct_start_date,
                    "ct_end_date": ct_link.ct_end_date,
                })

        items.append({
            "co_id": contract.co_id,
            "co_code": contract.co_code,
            "co_observations": contract.co_observations,
            "co_value_contracted": float(contract.co_value_contracted) if contract.co_value_contracted else None,
            "co_value_consumed": float(contract.co_value_consumed) if contract.co_value_consumed else None,
            "co_value_alarm": float(contract.co_value_alarm) if contract.co_value_alarm else None,
            "co_billing_type": contract.co_billing_type,
            "co_contract_number": contract.co_contract_number,
            "co_number_poliza": contract.co_number_poliza,
            "co_active": contract.co_active,
            "co_enterprise_id": contract.co_enterprise_id,
            "co_created_at": contract.co_created_at,
            "co_updated_at": contract.co_updated_at,
            "enterprise": {
                "en_id": contract.enterprise.en_id,
                "en_code": contract.enterprise.en_code,
                "en_name": contract.enterprise.en_name,
            } if contract.enterprise else None,
            "tariffs": tariffs,
        })

    return {
        "enterprise_id": enterprise_id,
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
    }


async def list_tariffs_by_contract(
    db: AsyncSession,
    contract_id: int,
    skip: int = 0,
    limit: int = 100,
    active: Optional[bool] = None
):
    """List paginated tariffs linked to a specific contract."""
    contract = await ContractTariffRepository.get_contract_by_id(db, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contrato con ID {contract_id} no encontrado"
        )

    items, total = await ContractTariffRepository.get_tariffs_by_contract_paginated(
        db, contract_id, skip, limit, active
    )
    return {
        "contract_id": contract_id,
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
    }
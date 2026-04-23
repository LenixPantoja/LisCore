from typing import Tuple, Sequence, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.domains.contractstariffs.domain.models import Contract, Tariff, TariffDetail, ContractTariff
from app.domains.orders.domain.models import Order
from app.domains.studieslab.domain.models import StudiesLab
from app.domains.studieslab.domain.models import StudiesLab as Studie
from app.domains.enterprises.domain.models import Enterprise

class ContractTariffRepository:
    # --- Tariff Methods ---
    
    @staticmethod
    async def create_tariff(db: AsyncSession, data: dict) -> Tariff:
        """Create a new tariff with optional details"""
        details_data = data.pop('details', [])
        
        tariff = Tariff(**data)
        db.add(tariff)
        await db.flush()  # Get tariff ID
        
        # Create tariff details if provided
        for detail_data in details_data:
            detail = TariffDetail(td_tariff_id=tariff.t_id, **detail_data)
            db.add(detail)
        
        await db.commit()
        await db.refresh(tariff)
        
        # Load details
        await db.refresh(tariff, attribute_names=['details'])
        
        return tariff

    @staticmethod
    async def get_tariffs(db: AsyncSession) -> List[Tariff]:
        """Get all tariffs with their details"""
        result = await db.execute(
            select(Tariff).options(
                selectinload(Tariff.details),
                selectinload(Tariff.contracts_link)
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_tariffs_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[Tariff], int]:
        """Get tariffs with pagination and optional filters"""
        query = select(Tariff).options(
            selectinload(Tariff.details),
            selectinload(Tariff.contracts_link)
        )

        # Filtros de búsqueda
        if search:
            query = query.filter(Tariff.t_name.ilike(f"%{search}%"))

        if active is not None:
            query = query.filter(Tariff.t_activo == active)

        # Conteo total para paginación
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Resultados paginados
        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Tariff.t_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_tariff_by_id(db: AsyncSession, tariff_id: int) -> Optional[Tariff]:
        """Get a tariff by ID with details"""
        result = await db.execute(
            select(Tariff)
            .filter(Tariff.t_id == tariff_id)
            .options(
                selectinload(Tariff.details),
                selectinload(Tariff.contracts_link)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def add_tariff_detail(db: AsyncSession, tariff_id: int, data: dict) -> TariffDetail:
        """Add a detail to an existing tariff"""
        detail = TariffDetail(td_tariff_id=tariff_id, **data)
        db.add(detail)
        await db.commit()
        await db.refresh(detail)
        return detail

    @staticmethod
    async def update_tariff(db: AsyncSession, tariff_id: int, update_data: dict) -> Optional[Tariff]:
        """Update a tariff"""
        tariff = await db.get(Tariff, tariff_id)
        if tariff:
            for key, value in update_data.items():
                setattr(tariff, key, value)
            await db.commit()
            await db.refresh(tariff)
        return tariff

    @staticmethod
    async def delete_tariff(db: AsyncSession, tariff_id: int) -> dict:
        """
        Delete a tariff and its associated details.
        Returns a dict with success status and message.
        Raises ValueError if tariff is used in orders.
        """
        tariff = await db.get(Tariff, tariff_id)
        if not tariff:
            return {"success": False, "message": "Tarifa no encontrada"}

        # Check if tariff is used in orders
        orders_count_stmt = select(func.count()).select_from(Order).where(Order.o_tariff_id == tariff_id)
        orders_count = (await db.execute(orders_count_stmt)).scalar() or 0

        if orders_count > 0:
            return {
                "success": False,
                "message": f"No se puede eliminar la tarifa porque está siendo usada en {orders_count} orden(es)",
                "orders_count": orders_count
            }

        await db.delete(tariff)
        await db.commit()
        return {"success": True, "message": "Tarifa eliminada exitosamente"}

    @staticmethod
    async def get_tariffs_by_enterprise(
        db: AsyncSession,
        enterprise_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[Tariff], int]:
        """Get tariffs associated with an enterprise via contracts, with pagination"""
        query = select(Tariff).join(
            ContractTariff, ContractTariff.ct_tariff_id == Tariff.t_id
        ).join(
            Contract, Contract.co_id == ContractTariff.ct_contract_id
        ).filter(
            Contract.co_enterprise_id == enterprise_id
        ).options(
            selectinload(Tariff.details)
        ).distinct()

        if search:
            query = query.filter(Tariff.t_name.ilike(f"%{search}%"))
        if active is not None:
            query = query.filter(Tariff.t_activo == active)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Tariff.t_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_tariff_studies_by_enterprise(
        db: AsyncSession,
        enterprise_id: int,
        tariff_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence, int]:
        """
        Get all studies for a tariff associated with an enterprise.
        Returns tariff details with full study info and tariff value.
        """
        # Verify enterprise-tariff relationship exists
        verify_query = select(Tariff).join(
            ContractTariff, ContractTariff.ct_tariff_id == Tariff.t_id
        ).join(
            Contract, Contract.co_id == ContractTariff.ct_contract_id
        ).filter(
            Contract.co_enterprise_id == enterprise_id,
            Tariff.t_id == tariff_id
        )
        verify_result = await db.execute(verify_query)
        if not verify_result.scalars().first():
            return [], 0

        # Get tariff details with study info
        query = select(
            TariffDetail,
            StudiesLab
        ).join(
            StudiesLab, StudiesLab.id == TariffDetail.td_studie_id
        ).filter(
            TariffDetail.td_tariff_id == tariff_id
        ).options(
            selectinload(TariffDetail.studie)
        )

        if search:
            query = query.filter(
                StudiesLab.name.ilike(f"%{search}%") | StudiesLab.code.ilike(f"%{search}%")
            )
        if active is not None:
            query = query.filter(StudiesLab.active == active)

        # Count
        count_query = select(func.count()).select_from(TariffDetail).filter(
            TariffDetail.td_tariff_id == tariff_id
        )
        total = (await db.execute(count_query)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(TariffDetail.td_id.asc())
        )
        rows = result.all()

        # Get tariff name
        tariff_result = await db.execute(select(Tariff).filter(Tariff.t_id == tariff_id))
        tariff = tariff_result.scalars().first()
        tariff_name = tariff.t_name if tariff else None

        return rows, total, tariff_name

    @staticmethod
    async def get_tariff_details_paginated(
        db: AsyncSession,
        tariff_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[TariffDetail], int]:
        """Get tariff details with pagination and study information"""
        # Verify tariff exists
        tariff = await db.get(Tariff, tariff_id)
        if not tariff:
            return [], 0

        query = select(TariffDetail).filter(
            TariffDetail.td_tariff_id == tariff_id
        ).options(
            selectinload(TariffDetail.studie)
        )

        # Join with StudiesLab for filtering
        if search:
            query = query.join(StudiesLab).filter(
                StudiesLab.name.ilike(f"%{search}%") | StudiesLab.code.ilike(f"%{search}%")
            )

        if active is not None:
            query = query.join(StudiesLab).filter(StudiesLab.active == active)

        # Count total
        count_query = select(func.count()).select_from(TariffDetail).filter(
            TariffDetail.td_tariff_id == tariff_id
        )
        total = (await db.execute(count_query)).scalar() or 0

        # Paginated results
        result = await db.execute(
            query.offset(skip).limit(limit).order_by(TariffDetail.td_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def update_tariff_detail(db: AsyncSession, detail_id: int, update_data: dict) -> Optional[TariffDetail]:
        """Update a tariff detail"""
        detail = await db.get(TariffDetail, detail_id)
        if not detail:
            return None

        for key, value in update_data.items():
            setattr(detail, key, value)

        await db.commit()
        await db.refresh(detail, attribute_names=['studie'])
        return detail

    @staticmethod
    async def delete_tariff_detail(db: AsyncSession, detail_id: int) -> dict:
        """Delete a tariff detail"""
        detail = await db.get(TariffDetail, detail_id)
        if not detail:
            return {"success": False, "message": "Detalle de tarifa no encontrado"}

        await db.delete(detail)
        await db.commit()
        return {"success": True, "message": "Detalle de tarifa eliminado exitosamente"}

    # --- Contract Methods ---
    
    @staticmethod
    async def get_contract_by_id(db: AsyncSession, contract_id: int) -> Optional[Contract]:
        """Get a contract by ID with its enterprise and linked tariffs"""
        result = await db.execute(
            select(Contract)
            .filter(Contract.co_id == contract_id)
            .options(
                selectinload(Contract.enterprise),
                selectinload(Contract.tariffs_link).selectinload(ContractTariff.tariff)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_contracts_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        enterprise_id: Optional[int] = None
    ) -> Tuple[Sequence[Contract], int]:
        query = (
            select(Contract)
            .join(Enterprise, Contract.co_enterprise_id == Enterprise.en_id, isouter=True)
            .options(selectinload(Contract.enterprise))
        )

        if search:
            query = query.filter(
                or_(
                    Contract.co_code.ilike(f"%{search}%"),
                    Enterprise.en_code.ilike(f"%{search}%"),
                    Enterprise.en_name.ilike(f"%{search}%"),
                    Enterprise.en_nit.ilike(f"%{search}%"),
                )
            )

        if enterprise_id:
            query = query.filter(Contract.co_enterprise_id == enterprise_id)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Contract.co_code.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_contracts_with_tariffs_by_enterprise(
        db: AsyncSession,
        enterprise_id: int,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[Contract], int]:
        """Get paginated contracts for an enterprise, each with its linked tariffs."""
        query = select(Contract).filter(
            Contract.co_enterprise_id == enterprise_id
        ).options(
            selectinload(Contract.tariffs_link).selectinload(ContractTariff.tariff)
        )

        if search:
            query = query.filter(
                Contract.co_code.ilike(f"%{search}%") |
                Contract.co_contract_number.ilike(f"%{search}%")
            )

        if active is not None:
            query = query.filter(Contract.co_active == active)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Contract.co_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def create_contract(db: AsyncSession, data: dict) -> Contract:
        """Create a new contract"""
        new_contract = Contract(**data)
        db.add(new_contract)
        await db.commit()

        result = await db.execute(
            select(Contract)
            .filter(Contract.co_id == new_contract.co_id)
            .options(selectinload(Contract.enterprise))
        )
        return result.scalars().first()

    @staticmethod
    async def update_contract(db: AsyncSession, contract_id: int, update_data: dict) -> Optional[Contract]:
        """Update a contract"""
        contract = await db.get(Contract, contract_id)
        if not contract:
            return None

        for key, value in update_data.items():
            setattr(contract, key, value)

        from datetime import date
        contract.co_updated_at = date.today()

        await db.commit()
        
        # Reload with enterprise relationship
        result = await db.execute(
            select(Contract)
            .filter(Contract.co_id == contract_id)
            .options(selectinload(Contract.enterprise))
        )
        return result.scalars().first()

    @staticmethod
    async def link_tariff_to_contract(db: AsyncSession, data: dict) -> dict:
        """
        Link a tariff to a contract.
        Validates that both contract and tariff exist before creating the link.
        Returns a dict with success status and the created link or error message.
        """
        contract_id = data.get('ct_contract_id')
        tariff_id = data.get('ct_tariff_id')

        # Validate contract exists
        contract = await db.get(Contract, contract_id)
        if not contract:
            return {
                "success": False,
                "message": f"El contrato con ID {contract_id} no existe."
            }

        # Validate tariff exists
        tariff = await db.get(Tariff, tariff_id)
        if not tariff:
            return {
                "success": False,
                "message": f"La tarifa con ID {tariff_id} no existe."
            }

        # Check if link already exists
        existing_link_stmt = select(ContractTariff).where(
            ContractTariff.ct_contract_id == contract_id,
            ContractTariff.ct_tariff_id == tariff_id
        )
        existing_result = await db.execute(existing_link_stmt)
        existing_link = existing_result.scalars().first()

        if existing_link:
            return {
                "success": False,
                "message": "La tarifa ya está vinculada a este contrato."
            }

        # Create the link
        try:
            link = ContractTariff(**data)
            db.add(link)
            await db.commit()
            await db.refresh(link)

            return {
                "success": True,
                "link": link
            }
        except IntegrityError:
            await db.rollback()
            return {
                "success": False,
                "message": "La tarifa ya está vinculada a este contrato."
            }

    @staticmethod
    async def get_contract_tariffs(db: AsyncSession, contract_id: int) -> List[ContractTariff]:
        """Get all tariffs linked to a contract"""
        result = await db.execute(
            select(ContractTariff)
            .filter(ContractTariff.ct_contract_id == contract_id)
            .options(
                selectinload(ContractTariff.tariff),
                selectinload(ContractTariff.contract)
            )
        )
        return result.scalars().all()

    @staticmethod
    async def unlink_tariff_from_contract(db: AsyncSession, contract_id: int, tariff_id: int) -> dict:
        """
        Unlink a tariff from a contract.
        Only allows unlinking if the tariff is NOT being used in any orders.
        Returns a dict with success status and message.
        """
        # Check if tariff exists
        tariff = await db.get(Tariff, tariff_id)
        if not tariff:
            return {
                "success": False,
                "message": f"La tarifa con ID {tariff_id} no existe."
            }

        # Check if contract exists
        contract = await db.get(Contract, contract_id)
        if not contract:
            return {
                "success": False,
                "message": f"El contrato con ID {contract_id} no existe."
            }

        # Find the link
        link_stmt = select(ContractTariff).where(
            ContractTariff.ct_contract_id == contract_id,
            ContractTariff.ct_tariff_id == tariff_id
        )
        result = await db.execute(link_stmt)
        link = result.scalars().first()

        if not link:
            return {
                "success": False,
                "message": "La tarifa no está vinculada a este contrato."
            }

        # Check if tariff is used in orders
        orders_count_stmt = select(func.count()).select_from(Order).where(Order.o_tariff_id == tariff_id)
        orders_count = (await db.execute(orders_count_stmt)).scalar() or 0

        if orders_count > 0:
            return {
                "success": False,
                "message": f"No se puede desvincular la tarifa porque está siendo usada en {orders_count} orden(es).",
                "orders_count": orders_count
            }

        # Delete the link
        ct_id = link.ct_id
        await db.delete(link)
        await db.commit()

        return {
            "success": True,
            "message": "Tarifa desvinculada exitosamente del contrato.",
            "ct_id": ct_id,
            "ct_contract_id": contract_id,
            "ct_tariff_id": tariff_id
        }

    @staticmethod
    async def get_tariffs_by_contract_paginated(
        db: AsyncSession,
        contract_id: int,
        skip: int = 0,
        limit: int = 100,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[Tariff], int]:
        """Get paginated tariffs linked to a specific contract, with optional active filter."""
        query = (
            select(Tariff)
            .join(ContractTariff, ContractTariff.ct_tariff_id == Tariff.t_id)
            .filter(ContractTariff.ct_contract_id == contract_id)
            .options(selectinload(Tariff.details))
        )

        if active is not None:
            query = query.filter(Tariff.t_activo == active)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Tariff.t_id.asc())
        )
        return result.scalars().all(), total